import asyncio
from pathlib import Path

from app.analysis import DeterministicAnalyzer
from app.collectors.router import CollectorRouter
from app.config import Settings
from app.evidence import EvidenceStore
from app.pipeline import MarketIntelligencePipeline
from app.reporting import HtmlReportGenerator
from app.schemas import SourceConfig, SourceKind
from app.storage import Repository


def build_pipeline(tmp_path: Path):
    settings = Settings(
        app_env="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        report_dir=tmp_path / "reports",
        raw_dir=tmp_path / "raw",
    )
    settings.ensure_directories()
    repository = Repository(settings.database_url)
    repository.init()
    repository.add_source(
        SourceConfig(
            name="离线测试信源",
            url="https://demo.example.com/feed",
            kind=SourceKind.DEMO,
        )
    )
    pipeline = MarketIntelligencePipeline(
        repository,
        CollectorRouter(settings),
        DeterministicAnalyzer(),
        HtmlReportGenerator(settings.report_dir),
        EvidenceStore(settings.raw_dir),
    )
    return repository, pipeline


def test_demo_pipeline_generates_report_and_deduplicates(tmp_path):
    repository, pipeline = build_pipeline(tmp_path)
    first = asyncio.run(pipeline.run())
    assert first.status == "success"
    assert first.collected_count == 4
    assert first.inserted_count == 3
    assert first.duplicate_count == 1
    assert Path(first.report_path).exists()
    assert len(repository.list_items()) == 3
    assert len(list((tmp_path / "raw" / "run-0001").glob("*.json"))) == 3
    assert all("raw_evidence_path" in item.metadata for item in repository.list_items())

    second = asyncio.run(pipeline.run())
    assert second.inserted_count == 0
    assert second.duplicate_count == 4
    assert len(repository.list_items()) == 3
    second_report = Path(second.report_path).read_text(encoding="utf-8")
    assert "本期共收录 3 条去重后的情报" in second_report


def test_scoped_run_uses_only_selected_sources_and_titles_report(tmp_path):
    repository, pipeline = build_pipeline(tmp_path)
    source = repository.list_sources()[0]
    result = asyncio.run(
        pipeline.run(
            sources_override=[source],
            report_title="储能行业市场情报报告",
            report_scope={
                "industry": "储能",
                "companies": ["示例公司"],
                "keywords": ["新品"],
            },
        )
    )
    report = Path(result.report_path).read_text(encoding="utf-8")
    assert result.source_count == 1
    assert "储能行业市场情报报告" in report
    assert "公司：示例公司" in report
