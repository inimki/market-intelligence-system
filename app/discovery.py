import ipaddress
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import quote_plus, urlparse

import httpx

from app.schemas import DiscoveredSource

SEARCH_URL = "https://www.so.com/s?q={query}"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
BLOCKED_DOMAINS = {
    "baidu.com",
    "bing.com",
    "so.com",
    "sogou.com",
    "zhihu.com",
    "weibo.com",
    "weixin.qq.com",
    "douyin.com",
    "toutiao.com",
    "bilibili.com",
    "bosszhipin.com",
    "liepin.com",
    "51job.com",
    "wikipedia.org",
    "qcc.com",
    "tianyancha.com",
    "163.com",
    "qq.com",
    "sina.com.cn",
    "sohu.com",
    "csdn.net",
    "jwview.com",
    "escn.com.cn",
}
NEWS_MARKERS = ("news", "press", "media", "新闻", "资讯", "动态", "公告")


@dataclass(slots=True)
class SearchCandidate:
    title: str
    url: str
    rank: int


class SearchResultParser(HTMLParser):
    """Extract direct destination URLs exposed by 360 search result headings."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_result_heading = False
        self.in_result_link = False
        self.current_url = ""
        self.current_title: list[str] = []
        self.results: list[SearchCandidate] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "h3" and "res-title" in (values.get("class") or ""):
            self.in_result_heading = True
        elif tag == "a" and self.in_result_heading:
            self.current_url = values.get("data-mdurl") or ""
            self.current_title = []
            self.in_result_link = bool(self.current_url)

    def handle_data(self, data: str) -> None:
        if self.in_result_link:
            self.current_title.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.in_result_link:
            title = " ".join("".join(self.current_title).split())
            self.results.append(
                SearchCandidate(title=title, url=self.current_url, rank=len(self.results) + 1)
            )
            self.in_result_link = False
            self.current_url = ""
        elif tag == "h3":
            self.in_result_heading = False


def is_public_web_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".local"):
        return False
    if any(hostname == domain or hostname.endswith(f".{domain}") for domain in BLOCKED_DOMAINS):
        return False
    try:
        address = ipaddress.ip_address(hostname.strip("[]"))
    except ValueError:
        return True
    return address.is_global


def score_candidate(candidate: SearchCandidate, company: str) -> int:
    parsed = urlparse(candidate.url)
    text = f"{candidate.title} {parsed.path}".lower()
    score = max(10, 100 - (candidate.rank - 1) * 12)
    if any(marker in text for marker in NEWS_MARKERS):
        score += 25
    if company.lower() in candidate.title.lower():
        score += 15
    if parsed.path in {"", "/"}:
        score -= 8
    return score


def parse_search_results(html: str) -> list[SearchCandidate]:
    parser = SearchResultParser()
    parser.feed(html)
    seen: set[str] = set()
    results: list[SearchCandidate] = []
    for candidate in parser.results:
        if candidate.url not in seen and is_public_web_url(candidate.url):
            seen.add(candidate.url)
            results.append(candidate)
    return results


async def _is_reachable(client: httpx.AsyncClient, url: str) -> tuple[bool, str]:
    try:
        async with client.stream("GET", url, follow_redirects=True) as response:
            final_url = str(response.url)
            content_type = response.headers.get("content-type", "").lower()
            usable = response.status_code < 400 and (
                not content_type or "html" in content_type or "text" in content_type
            )
            return usable and is_public_web_url(final_url), final_url
    except httpx.HTTPError:
        return False, url


async def discover_company_sources(
    industry: str, companies: list[str]
) -> tuple[list[DiscoveredSource], list[str]]:
    discoveries: list[DiscoveredSource] = []
    warnings: list[str] = []
    timeout = httpx.Timeout(20, connect=10)
    async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
        for company in companies:
            # 行业用于报告范围和标签；公司官网发现使用更短的查询，中文搜索结果更准确。
            query = f"{company} 官网 新闻中心"
            try:
                response = await client.get(SEARCH_URL.format(query=quote_plus(query)))
                response.raise_for_status()
            except httpx.HTTPError as exc:
                warnings.append(f"{company}：搜索失败（{exc}）")
                continue

            candidates = sorted(
                parse_search_results(response.text),
                key=lambda candidate: score_candidate(candidate, company),
                reverse=True,
            )
            selected: tuple[SearchCandidate, str] | None = None
            for candidate in candidates[:5]:
                reachable, final_url = await _is_reachable(client, candidate.url)
                if reachable:
                    selected = candidate, final_url
                    break
            if not selected:
                warnings.append(f"{company}：没有找到可访问的公开官网新闻页面，未自动加入")
                continue

            candidate, final_url = selected
            score = score_candidate(candidate, company)
            confidence = "高" if score >= 100 else "中"
            discoveries.append(
                DiscoveredSource(
                    company=company,
                    name=f"{company}官方新闻",
                    url=final_url,
                    search_query=query,
                    confidence=confidence,
                )
            )
    return discoveries, warnings
