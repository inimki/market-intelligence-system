from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.analysis import PandasAIAnalyzer
from app.config import get_settings
from app.schemas import IntelItem


class AnalysisRequest(BaseModel):
    items: list[IntelItem]
    question: str = Field(min_length=3, max_length=1000)


app = FastAPI(title="Market Intelligence PandasAI Service", version="0.1.0")


@app.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "service": "pandasai",
        "provider": settings.ai_provider,
        "model": settings.ai_model,
        "configured": bool(settings.ai_api_key or settings.openai_api_key),
    }


@app.post("/ask")
def ask(request: AnalysisRequest) -> dict:
    settings = get_settings()
    api_key = settings.ai_api_key or settings.openai_api_key
    if not api_key:
        raise HTTPException(status_code=503, detail="AI_API_KEY is not configured")
    try:
        answer = PandasAIAnalyzer(
            api_key=api_key,
            model=settings.ai_model,
            provider=settings.ai_provider,
            api_base=settings.ai_base_url,
        ).ask(request.items, request.question)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"answer": answer, "item_count": len(request.items)}
