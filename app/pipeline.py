from app.analysis import DeterministicAnalyzer
from app.collectors.router import CollectorRouter
from app.evidence import EvidenceStore
from app.normalization import to_intel_item
from app.reporting import HtmlReportGenerator
from app.schemas import IntelItem, RunResult, SourceConfig
from app.storage import Repository


class MarketIntelligencePipeline:
    def __init__(
        self,
        repository: Repository,
        router: CollectorRouter,
        analyzer: DeterministicAnalyzer,
        reporter: HtmlReportGenerator,
        evidence_store: EvidenceStore | None = None,
    ):
        self.repository = repository
        self.router = router
        self.analyzer = analyzer
        self.reporter = reporter
        self.evidence_store = evidence_store

    async def run(
        self,
        sources_override: list[SourceConfig] | None = None,
        report_title: str | None = None,
        report_scope: dict[str, object] | None = None,
    ) -> RunResult:
        run_id = self.repository.create_run()
        sources = (
            sources_override
            if sources_override is not None
            else self.repository.list_sources(enabled_only=True)
        )
        collected_count = inserted_count = duplicate_count = failed_count = 0
        errors: list[str] = []
        batch_items: dict[tuple[str, str], IntelItem] = {}

        for source in sources:
            try:
                documents = await self.router.collect(source)
                collected_count += len(documents)
                for document in documents:
                    evidence_path = None
                    if self.evidence_store:
                        evidence_path = self.evidence_store.save(run_id, document)
                    item = to_intel_item(document)
                    if evidence_path:
                        item.metadata["raw_evidence_path"] = str(evidence_path)
                    batch_items[(item.canonical_url, item.content_hash)] = item
                    if self.repository.insert_item(item):
                        inserted_count += 1
                    else:
                        duplicate_count += 1
            except Exception as exc:  # noqa: BLE001 - 一个信源失败不能中断整个批次
                failed_count += 1
                errors.append(f"{source.name}: {exc}")

        items = list(batch_items.values())
        report_path = None
        try:
            analysis = self.analyzer.analyze(items)
            report_path = self.reporter.generate(
                run_id,
                items,
                analysis,
                title=report_title,
                scope=report_scope,
            )
        except Exception as exc:  # noqa: BLE001 - persist report failures in run history
            errors.append(f"报告生成失败: {exc}")
            failed_count += 1
        if report_path is None:
            status = "failed"
        else:
            status = "success" if failed_count == 0 else ("partial" if collected_count else "failed")
        stats = {
            "source_count": len(sources),
            "collected_count": collected_count,
            "inserted_count": inserted_count,
            "duplicate_count": duplicate_count,
            "failed_count": failed_count,
            "errors": errors,
        }
        report_value = str(report_path) if report_path else None
        self.repository.finish_run(run_id, status, stats, report_value)
        return RunResult(run_id=run_id, status=status, report_path=report_value, **stats)
