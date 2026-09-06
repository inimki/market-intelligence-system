from functools import lru_cache

from app.analysis import DeterministicAnalyzer
from app.collectors import CollectorRouter
from app.config import get_settings
from app.evidence import EvidenceStore
from app.pipeline import MarketIntelligencePipeline
from app.reporting import HtmlReportGenerator
from app.storage import Repository


@lru_cache
def get_repository() -> Repository:
    repository = Repository(get_settings().database_url)
    repository.init()
    return repository


def get_pipeline() -> MarketIntelligencePipeline:
    settings = get_settings()
    return MarketIntelligencePipeline(
        repository=get_repository(),
        router=CollectorRouter(settings),
        analyzer=DeterministicAnalyzer(),
        reporter=HtmlReportGenerator(settings.report_dir),
        evidence_store=EvidenceStore(settings.raw_dir),
    )
