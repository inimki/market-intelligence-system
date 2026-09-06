from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from app import __version__
from app.config import get_settings
from app.dependencies import get_pipeline, get_repository
from app.discovery import discover_company_sources
from app.presentation import format_beijing_time
from app.schemas import (
    AnalysisAnswer,
    AnalysisQuestion,
    ResearchRequest,
    ResearchResult,
    RunRecord,
    RunResult,
    SourceConfig,
    SourceKind,
)

app = FastAPI(
    title="市场情报自动收集与报告系统",
    description="基于 Crawl4AI、Browser Use、PandasAI、n8n 与 Python 的中文市场情报服务",
    version=__version__,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

templates.env.filters["beijing_time"] = format_beijing_time


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard(request: Request) -> HTMLResponse:
    """展示中文系统控制台。"""
    repository = get_repository()
    sources = repository.list_sources()
    runs = repository.list_runs(limit=6)
    items = repository.list_items(limit=12)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html.j2",
        context={
            "version": __version__,
            "sources": sources,
            "enabled_source_count": sum(source.enabled for source in sources),
            "runs": runs,
            "items": items,
            "latest_run": runs[0] if runs else None,
        },
    )


@app.get("/health", summary="检查系统状态", tags=["系统"])
def health() -> dict:
    return {"status": "ok", "message": "系统运行正常", "version": __version__}


@app.get("/api/sources", response_model=list[SourceConfig], summary="查看全部信源", tags=["信源"])
def list_sources() -> list[SourceConfig]:
    return get_repository().list_sources()


@app.post("/api/sources", response_model=SourceConfig, summary="新增或更新信源", tags=["信源"])
def create_source(source: SourceConfig) -> SourceConfig:
    return get_repository().add_source(source)


@app.get("/api/items", summary="查看已收集情报", tags=["情报"])
def list_items(limit: int = 100):
    return get_repository().list_items(limit=min(max(limit, 1), 1000))


@app.post("/api/runs", response_model=RunResult, summary="立即运行完整流水线", tags=["运行"])
async def run_pipeline() -> RunResult:
    return await get_pipeline().run()


@app.post(
    "/api/research",
    response_model=ResearchResult,
    summary="按行业和公司自动发现信源并生成报告",
    tags=["智能调研"],
)
async def create_research(brief: ResearchRequest) -> ResearchResult:
    discoveries, warnings = await discover_company_sources(brief.industry, brief.companies)
    repository = get_repository()
    sources: list[SourceConfig] = []
    for discovery in discoveries:
        source = repository.add_source(
            SourceConfig(
                name=discovery.name,
                url=discovery.url,
                kind=SourceKind.STATIC,
                enabled=True,
                tags=[brief.industry, discovery.company, *brief.keywords, "自动发现"],
                extraction_hint=(
                    f"行业：{brief.industry}；公司：{discovery.company}；"
                    f"关注：{'、'.join(brief.keywords) if brief.keywords else '企业动态'}"
                ),
            )
        )
        repository.disable_other_discovered_sources(discovery.company, str(discovery.url))
        sources.append(source)

    if not sources:
        return ResearchResult(
            status="no_sources",
            industry=brief.industry,
            companies=brief.companies,
            warnings=warnings,
        )

    run = await get_pipeline().run(
        sources_override=sources,
        report_title=f"{brief.industry}市场情报报告",
        report_scope={
            "industry": brief.industry,
            "companies": brief.companies,
            "keywords": brief.keywords,
        },
    )
    filename = Path(run.report_path).name if run.report_path else None
    status = run.status
    if warnings and status == "success":
        status = "partial"
    return ResearchResult(
        status=status,
        industry=brief.industry,
        companies=brief.companies,
        discovered_sources=discoveries,
        run=run,
        report_url=f"/reports/{filename}" if filename else None,
        download_url=f"/reports/{filename}/download" if filename else None,
        warnings=warnings,
    )


@app.get("/api/runs", response_model=list[RunRecord], summary="查看运行记录", tags=["运行"])
def list_runs(limit: int = 50) -> list[RunRecord]:
    return get_repository().list_runs(limit=min(max(limit, 1), 500))


@app.post(
    "/api/analysis/ask",
    response_model=AnalysisAnswer,
    summary="用自然语言询问已收集数据",
    tags=["AI 分析"],
)
async def ask_analysis(request: AnalysisQuestion) -> AnalysisAnswer:
    """Send stored evidence to the isolated PandasAI service."""
    settings = get_settings()
    if not settings.analysis_service_url:
        raise HTTPException(status_code=503, detail="ANALYSIS_SERVICE_URL is not configured")

    items = get_repository().list_items(limit=request.item_limit)
    payload = {
        "question": request.question,
        "items": [item.model_dump(mode="json") for item in items],
    }
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{settings.analysis_service_url.rstrip('/')}/ask", json=payload
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:1000]
        status_code = 503 if exc.response.status_code == 503 else 502
        raise HTTPException(
            status_code=status_code, detail=f"analysis service failed: {detail}"
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"analysis service unavailable: {exc}") from exc
    return AnalysisAnswer.model_validate(response.json())


@app.get("/reports/latest", summary="打开最新中文报告", tags=["报告"])
def get_latest_report() -> FileResponse:
    runs = get_repository().list_runs(limit=100)
    latest = next((run for run in runs if run.report_path), None)
    if not latest or not latest.report_path:
        raise HTTPException(status_code=404, detail="report not found")
    report_path = Path(latest.report_path).resolve()
    if report_path.parent != get_settings().report_dir.resolve() or not report_path.exists():
        raise HTTPException(status_code=404, detail="report not found")
    return FileResponse(report_path, media_type="text/html; charset=utf-8")


@app.get("/reports/latest/download", summary="下载最新中文报告", tags=["报告"])
def download_latest_report() -> FileResponse:
    runs = get_repository().list_runs(limit=100)
    latest = next((run for run in runs if run.report_path), None)
    if not latest or not latest.report_path:
        raise HTTPException(status_code=404, detail="report not found")
    report_path = Path(latest.report_path).resolve()
    if report_path.parent != get_settings().report_dir.resolve() or not report_path.exists():
        raise HTTPException(status_code=404, detail="report not found")
    return FileResponse(report_path, media_type="text/html", filename=report_path.name)


@app.get("/reports/{filename}", summary="按文件名打开报告", tags=["报告"])
def get_report(filename: str) -> FileResponse:
    safe_name = Path(filename).name
    report_path = (get_settings().report_dir / safe_name).resolve()
    if report_path.parent != get_settings().report_dir.resolve() or not report_path.exists():
        raise HTTPException(status_code=404, detail="report not found")
    return FileResponse(report_path, media_type="text/html; charset=utf-8")


@app.get("/reports/{filename}/download", summary="按文件名下载报告", tags=["报告"])
def download_report(filename: str) -> FileResponse:
    safe_name = Path(filename).name
    report_path = (get_settings().report_dir / safe_name).resolve()
    if report_path.parent != get_settings().report_dir.resolve() or not report_path.exists():
        raise HTTPException(status_code=404, detail="report not found")
    return FileResponse(report_path, media_type="text/html", filename=report_path.name)
