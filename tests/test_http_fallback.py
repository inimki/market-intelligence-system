from app.collectors.crawl4ai_collector import _VisibleTextParser


def test_visible_text_parser_keeps_page_copy_and_drops_scripts():
    parser = _VisibleTextParser()
    parser.feed(
        "<html><head><title>公司新闻</title><script>secret()</script></head>"
        "<body><h1>最新动态</h1><p>发布新产品。</p></body></html>"
    )
    assert parser.title == "公司新闻"
    assert "最新动态" in parser.text
    assert "发布新产品" in parser.text
    assert "secret" not in parser.text
