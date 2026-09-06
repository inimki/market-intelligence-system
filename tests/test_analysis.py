from datetime import UTC, datetime

from app.analysis import DeterministicAnalyzer, PandasAIAnalyzer
from app.schemas import IntelItem


def make_item(source: str, title: str, content_hash: str) -> IntelItem:
    return IntelItem(
        source_name=source,
        source_url="https://example.com",
        url=f"https://example.com/{content_hash}",
        canonical_url=f"https://example.com/{content_hash}",
        title=title,
        content=f"{title} 的市场情报正文",
        published_at=datetime(2026, 8, 30, tzinfo=UTC),
        content_hash=content_hash.ljust(64, "0"),
    )


def test_analysis_counts_are_reproducible():
    items = [
        make_item("信源A", "工业自动化", "a"),
        make_item("信源A", "预测性维护", "b"),
        make_item("信源B", "渠道扩张", "c"),
    ]

    result = DeterministicAnalyzer().analyze(items)

    assert result.total_items == 3
    assert result.source_count == 2
    assert result.items_by_source[0] == {"source": "信源A", "count": 2}
    assert result.items_by_day == [{"day": "2026-08-30", "count": 3}]


def test_deepseek_litellm_configuration():
    analyzer = PandasAIAnalyzer(
        api_key="test-key",
        provider="deepseek",
        api_base="https://api.deepseek.com",
        model="deepseek-v4-flash",
    )

    assert analyzer._litellm_model() == "deepseek/deepseek-v4-flash"
    assert analyzer._litellm_options() == {
        "api_key": "test-key",
        "api_base": "https://api.deepseek.com",
        "timeout": 90,
        "extra_body": {"thinking": {"type": "disabled"}},
    }
