from app.normalization import (
    canonicalize_url,
    extract_evidence,
    make_content_hash,
    make_summary,
    markdown_to_plain_text,
    normalize_text,
    normalize_title,
)


def test_canonicalize_url_removes_tracking_and_fragment():
    assert (
        canonicalize_url("HTTPS://Example.COM/news/?utm_source=x&b=2&a=1#title")
        == "https://example.com/news?a=1&b=2"
    )


def test_hash_is_stable_for_whitespace_and_case():
    left = make_content_hash("New Product", "Hello   World")
    right = make_content_hash("new product", " hello world ")
    assert left == right


def test_normalize_text():
    assert normalize_text("  市场\n\n 情报  ") == "市场 情报"


def test_markdown_is_converted_to_readable_plain_text():
    markdown = """
    ![](data:image/svg+xml,%3csvg%20viewBox='0%200%2064%2064'%3e)
    1. [Home](https://example.com/)
    2. 新闻中心
    ![工厂新产线](https://example.com/factory.jpg)
    公司在上海发布新一代工业自动化平台。
    """
    cleaned = markdown_to_plain_text(markdown)
    assert "data:image" not in cleaned
    assert "https://" not in cleaned
    assert "![]" not in cleaned
    assert "工厂新产线" in cleaned
    assert "公司在上海发布新一代工业自动化平台。" in cleaned


def test_summary_and_evidence_do_not_show_markdown_noise():
    content = "![](https://example.com/a.png) [新闻中心](https://example.com/news) 企业发布储能新品。"
    assert "https://" not in make_summary(content)
    assert extract_evidence(content) == ["新闻中心 企业发布储能新品。"]
    assert normalize_title(" | Schneider Electric 中国 ") == "Schneider Electric 中国"
