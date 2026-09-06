import json
from datetime import datetime
from pathlib import Path

from app.collectors.base import BaseCollector
from app.schemas import CollectedDocument, SourceConfig


class DemoCollector(BaseCollector):
    def __init__(self, fixture_path: Path | None = None):
        self.fixture_path = (
            fixture_path or Path(__file__).parents[2] / "data" / "demo_documents.json"
        )

    async def collect(self, source: SourceConfig) -> list[CollectedDocument]:
        payload = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        return [
            CollectedDocument(
                source_name=source.name,
                source_url=source.url,
                final_url=document["url"],
                title=document["title"],
                content=document["content"],
                published_at=datetime.fromisoformat(document["published_at"]),
                author=document.get("author"),
                metadata={
                    "collector": "demo",
                    "fixture": self.fixture_path.name,
                    "source_tags": source.tags,
                },
            )
            for document in payload
        ]
