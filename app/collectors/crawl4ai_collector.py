import re
from html.parser import HTMLParser
from typing import ClassVar

import httpx

from app.collectors.base import BaseCollector, CollectorError
from app.schemas import CollectedDocument, SourceConfig


class _VisibleTextParser(HTMLParser):
    block_tags: ClassVar[set[str]] = {
        "article",
        "br",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "li",
        "main",
        "p",
        "section",
        "td",
        "th",
    }
    ignored_tags: ClassVar[set[str]] = {"script", "style", "noscript", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ignored_depth = 0
        self.in_title = False
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.ignored_tags:
            self.ignored_depth += 1
        elif not self.ignored_depth and tag == "title":
            self.in_title = True
        elif not self.ignored_depth and tag in self.block_tags:
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.ignored_tags and self.ignored_depth:
            self.ignored_depth -= 1
        elif tag == "title":
            self.in_title = False
        elif not self.ignored_depth and tag in self.block_tags:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.ignored_depth:
            return
        if self.in_title:
            self.title_parts.append(data)
        self.text_parts.append(data)

    @property
    def title(self) -> str:
        return " ".join("".join(self.title_parts).split())

    @property
    def text(self) -> str:
        lines = (" ".join(line.split()) for line in "".join(self.text_parts).splitlines())
        return "\n".join(line for line in lines if line)


class Crawl4AICollector(BaseCollector):
    async def collect(self, source: SourceConfig) -> list[CollectedDocument]:
        try:
            from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
            from crawl4ai.content_filter_strategy import PruningContentFilter
            from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
        except ImportError as exc:
            raise CollectorError(
                "Crawl4AI 未安装。请执行 pip install -e '.[collectors]' 后重试。"
            ) from exc

        markdown_generator = DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(
                threshold=0.48,
                threshold_type="dynamic",
                min_word_threshold=5,
            )
        )
        config = CrawlerRunConfig(
            cache_mode=CacheMode.ENABLED,
            markdown_generator=markdown_generator,
            exclude_external_links=True,
            exclude_social_media_links=True,
            page_timeout=25_000,
        )
        try:
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=str(source.url), config=config)
        except Exception as exc:  # noqa: BLE001 - 失败后降级到公开静态 HTML
            return await self._plain_http_fallback(source, f"Crawl4AI 请求失败: {exc}")

        if not result.success:
            return await self._plain_http_fallback(
                source, result.error_message or "Crawl4AI 返回失败状态"
            )

        metadata = result.metadata or {}
        markdown = ""
        if result.markdown:
            fitted_markdown = result.markdown.fit_markdown or ""
            chinese_character_count = len(re.findall(r"[\u4e00-\u9fff]", fitted_markdown))
            if len(fitted_markdown) >= 500 and chinese_character_count >= 50:
                markdown = fitted_markdown
            else:
                markdown = result.markdown.raw_markdown
        title = metadata.get("title") or source.name
        if not markdown.strip():
            return await self._plain_http_fallback(source, "Crawl4AI 没有得到可用正文")

        return [
            CollectedDocument(
                source_name=source.name,
                source_url=source.url,
                final_url=result.url or source.url,
                title=title,
                content=markdown,
                raw_html=result.html,
                metadata={
                    "collector": "crawl4ai",
                    "status_code": result.status_code,
                    "page_metadata": metadata,
                    "source_tags": source.tags,
                },
            )
        ]

    async def _plain_http_fallback(
        self, source: SourceConfig, fallback_reason: str
    ) -> list[CollectedDocument]:
        """Use public HTML only when browser rendering fails; never bypass access controls."""
        try:
            async with httpx.AsyncClient(
                timeout=25,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
                    )
                },
            ) as client:
                response = await client.get(str(source.url))
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise CollectorError(f"{fallback_reason}；普通网页请求也失败: {exc}") from exc

        parser = _VisibleTextParser()
        parser.feed(response.text)
        content = parser.text
        if len(content) < 200:
            raise CollectorError(f"{fallback_reason}；普通网页请求未得到足够正文")
        return [
            CollectedDocument(
                source_name=source.name,
                source_url=source.url,
                final_url=str(response.url),
                title=parser.title or source.name,
                content=content,
                raw_html=response.text,
                metadata={
                    "collector": "plain-http-fallback",
                    "status_code": response.status_code,
                    "fallback_reason": fallback_reason[:500],
                    "source_tags": source.tags,
                },
            )
        ]
