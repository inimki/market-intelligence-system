from app.discovery import is_public_web_url, parse_search_results, score_candidate


def test_parse_search_results_uses_direct_url_and_filters_aggregators():
    html = """
    <h3 class="res-title"><a href="/redirect" data-mdurl="https://www.catl.com/news/">
      <em>新闻</em>中心
    </a></h3>
    <h3 class="res-title"><a data-mdurl="https://www.zhihu.com/question/1">讨论</a></h3>
    """
    results = parse_search_results(html)
    assert len(results) == 1
    assert results[0].title == "新闻中心"
    assert results[0].url == "https://www.catl.com/news/"
    assert score_candidate(results[0], "宁德时代") >= 100


def test_public_url_guard_blocks_local_and_search_platforms():
    assert is_public_web_url("https://www.example.com/news")
    assert not is_public_web_url("http://127.0.0.1/admin")
    assert not is_public_web_url("http://localhost:8000")
    assert not is_public_web_url("https://news.zhihu.com/story")
