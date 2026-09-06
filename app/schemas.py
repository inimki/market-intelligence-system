from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class SourceKind(StrEnum):
    DEMO = "demo"
    STATIC = "static"
    INTERACTIVE = "interactive"


class SourceConfig(BaseModel):
    id: int | None = None
    name: str = Field(min_length=1, max_length=200)
    url: HttpUrl
    kind: SourceKind = SourceKind.STATIC
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)
    extraction_hint: str | None = None


class CollectedDocument(BaseModel):
    source_name: str
    source_url: HttpUrl
    final_url: HttpUrl
    title: str
    content: str
    published_at: datetime | None = None
    author: str | None = None
    raw_html: str | None = None
    screenshot_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IntelItem(BaseModel):
    id: int | None = None
    source_name: str
    source_url: str
    url: str
    canonical_url: str
    title: str
    content: str
    summary: str = ""
    published_at: datetime | None = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    author: str | None = None
    keywords: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    content_hash: str
    status: str = "ok"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", "content")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class RunResult(BaseModel):
    run_id: int
    status: str
    source_count: int
    collected_count: int
    inserted_count: int
    duplicate_count: int
    failed_count: int
    report_path: str | None = None
    errors: list[str] = Field(default_factory=list)


class RunRecord(BaseModel):
    id: int
    started_at: datetime
    finished_at: datetime | None = None
    status: str
    report_path: str | None = None
    stats: dict[str, Any] = Field(default_factory=dict)


class AnalysisQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    item_limit: int = Field(default=500, ge=1, le=5000)


class AnalysisAnswer(BaseModel):
    answer: str
    item_count: int


class ResearchRequest(BaseModel):
    industry: str = Field(min_length=2, max_length=100)
    companies: list[str] = Field(min_length=1, max_length=8)
    keywords: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("industry")
    @classmethod
    def clean_industry(cls, value: str) -> str:
        return value.strip()

    @field_validator("companies", "keywords")
    @classmethod
    def clean_terms(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            term = value.strip()
            if term and term not in cleaned:
                cleaned.append(term)
        if not cleaned and values:
            raise ValueError("不能只填写空白内容")
        return cleaned


class DiscoveredSource(BaseModel):
    company: str
    name: str
    url: HttpUrl
    search_query: str
    confidence: str


class ResearchResult(BaseModel):
    status: str
    industry: str
    companies: list[str]
    discovered_sources: list[DiscoveredSource] = Field(default_factory=list)
    run: RunResult | None = None
    report_url: str | None = None
    download_url: str | None = None
    warnings: list[str] = Field(default_factory=list)
