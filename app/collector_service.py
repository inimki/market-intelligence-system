from fastapi import FastAPI, HTTPException

from app.collectors.browser_use_collector import BrowserUseCollector
from app.collectors.crawl4ai_collector import Crawl4AICollector
from app.config import get_settings
from app.schemas import CollectedDocument, SourceConfig, SourceKind

app = FastAPI(title="Market Intelligence Collector", version="0.1.0")


@app.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "service": "collector",
        "browser_use_provider": (
            "browser-use-cloud" if settings.browser_use_api_key else settings.ai_provider
        ),
        "browser_use_configured": bool(
            settings.browser_use_api_key or settings.ai_api_key or settings.openai_api_key
        ),
    }


@app.post("/collect", response_model=list[CollectedDocument])
async def collect(source: SourceConfig) -> list[CollectedDocument]:
    if source.kind == SourceKind.STATIC:
        collector = Crawl4AICollector()
    elif source.kind == SourceKind.INTERACTIVE:
        settings = get_settings()
        collector = BrowserUseCollector(
            browser_use_api_key=settings.browser_use_api_key,
            ai_api_key=settings.ai_api_key or settings.openai_api_key,
            ai_provider=settings.ai_provider,
            ai_base_url=settings.ai_base_url,
            ai_model=settings.ai_model,
        )
    else:
        raise HTTPException(status_code=400, detail="collector service only accepts real sources")
    try:
        return await collector.collect(source)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
