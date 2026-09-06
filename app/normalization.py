import hashlib
import html
import re
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.schemas import CollectedDocument, IntelItem

TRACKING_QUERY_PREFIXES = ("utm_", "spm", "from", "source")
MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\([^\n]*?\)")
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]*)\]\([^\n]*?\)")
BARE_URL_PATTERN = re.compile(r"(?:https?://|data:image/)[^\s<>]+", re.IGNORECASE)
MARKDOWN_PREFIX_PATTERN = re.compile(r"^\s*(?:#{1,6}|>|[-+*]|\d+[.)])\s*")
NAVIGATION_LABELS = {
    "home",
    "skip to main content",
    "首页",
    "主页",
    "菜单",
    "搜索",
    "返回顶部",
}
EVIDENCE_NOISE_TERMS = {
    "cookie",
    "products",
    "logo",
    "toggle",
    "sign in",
    "登录/注册",
    "shopping list",
    "suggestions",
    "see more",
    "where to buy",
    "产品文档",
    "软件下载",
    "获取报价",
    "公司介绍",
    "投资者",
    "查看更多",
    "返回顶部",
}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def markdown_to_plain_text(value: str) -> str:
    """移除采集结果中的 Markdown 图片、链接和导航噪声。"""

    def replace_image(match: re.Match) -> str:
        alt_text = normalize_text(match.group(1))
        lower_alt = alt_text.lower()
        if (
            len(alt_text) < 4
            or lower_alt
            in {
                "all",
                "image",
                "logo",
                "图片",
                "图像",
                "product",
                "service",
                "industry",
                "contact",
            }
            or any(
                token in lower_alt
                for token in (" logo", "icon", "toggle", ".jpg", ".jpeg", ".png", ".svg")
            )
        ):
            return "\n"
        return f"\n{alt_text}\n"

    text = html.unescape(value.replace("\u00a0", " "))
    text = MARKDOWN_IMAGE_PATTERN.sub(replace_image, text)
    text = MARKDOWN_LINK_PATTERN.sub(lambda match: f" {match.group(1)} ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = BARE_URL_PATTERN.sub(" ", text)
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)

    cleaned_lines: list[str] = []
    for raw_line in text.splitlines():
        line = MARKDOWN_PREFIX_PATTERN.sub("", raw_line)
        line = re.sub(r"\s*#{1,6}\s*", " ", line)
        line = re.sub(r"[`*_~|\\]+", " ", line)
        line = normalize_text(line).strip("-–—·|:：")
        line = re.sub(r"^(?:all|clear)\s+", "", line, flags=re.IGNORECASE)
        if not line or line.lower() in NAVIGATION_LABELS:
            continue
        if not re.search(r"[A-Za-z0-9\u4e00-\u9fff]", line):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def normalize_title(value: str) -> str:
    return normalize_text(value).strip(" -–—·|:：")


def meaningful_sentences(content: str, limit: int = 2) -> list[str]:
    """优先选择正文陈述，降低菜单、按钮和英文图片说明的权重。"""
    text = markdown_to_plain_text(content)
    candidates: list[tuple[int, int, str]] = []
    for position, match in enumerate(re.finditer(r"[^。！？!?\n]+[。！？!?]?", text)):
        sentence = normalize_text(match.group()).strip(" -–—·|:：")
        chinese_count = len(re.findall(r"[\u4e00-\u9fff]", sentence))
        if chinese_count < 8 or len(sentence) > 320:
            continue
        lower_sentence = sentence.lower()
        noise_count = sum(term in lower_sentence for term in EVIDENCE_NOISE_TERMS)
        if noise_count >= 2 or "登录/注册" in sentence or "sign in" in lower_sentence:
            continue
        english_count = len(re.findall(r"[A-Za-z]{3,}", sentence))
        length_penalty = max(0, len(sentence) - 180) * 3
        score = chinese_count * 3 - english_count * 2 - noise_count * 80 - length_penalty
        if sentence.endswith(("。", "！", "？", ".", "!", "?")):
            score += 25
        candidates.append((score, position, sentence))
    selected = sorted(candidates, key=lambda row: (-row[0], row[1]))[:limit]
    return [sentence for _, _, sentence in sorted(selected, key=lambda row: row[1])]


def canonicalize_url(value: str) -> str:
    parsed = urlsplit(value)
    query = [
        (key, val)
        for key, val in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith(TRACKING_QUERY_PREFIXES)
    ]
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), path, urlencode(sorted(query)), "")
    )


def make_content_hash(title: str, content: str) -> str:
    stable_text = normalize_text(f"{title}\n{content}").lower()
    return hashlib.sha256(stable_text.encode("utf-8")).hexdigest()


def make_summary(content: str, limit: int = 220) -> str:
    text = markdown_to_plain_text(content)
    sentences = meaningful_sentences(text, limit=2)
    summary = " ".join(sentences) or normalize_text(text)
    return summary if len(summary) <= limit else f"{summary[:limit].rstrip()}…"


def extract_evidence(content: str, limit: int = 260) -> list[str]:
    text = markdown_to_plain_text(content)
    sentences = meaningful_sentences(text, limit=2)
    if sentences:
        return [sentence[:limit] for sentence in sentences[:2]]
    fallback = normalize_text(text)
    return [fallback[:limit]] if fallback else ["未提取到有效正文，请打开原始来源核验。"]


def to_intel_item(document: CollectedDocument) -> IntelItem:
    title = normalize_title(document.title)
    content = markdown_to_plain_text(document.content)
    url = str(document.final_url)
    published_at = document.published_at
    if published_at and published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)
    return IntelItem(
        source_name=document.source_name,
        source_url=str(document.source_url),
        url=url,
        canonical_url=canonicalize_url(url),
        title=title,
        content=content,
        summary=make_summary(content),
        published_at=published_at,
        collected_at=datetime.now(UTC),
        author=document.author,
        evidence=extract_evidence(content),
        content_hash=make_content_hash(title, content),
        metadata=document.metadata,
    )
