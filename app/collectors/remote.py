import httpx

from app.collectors.base import BaseCollector, CollectorError
from app.schemas import CollectedDocument, SourceConfig


class RemoteCollector(BaseCollector):
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def collect(self, source: SourceConfig) -> list[CollectedDocument]:
        try:
            async with httpx.AsyncClient(timeout=600) as client:
                response = await client.post(
                    f"{self.base_url}/collect", json=source.model_dump(mode="json")
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise CollectorError(f"远程采集服务请求失败: {exc}") from exc
        return [CollectedDocument.model_validate(item) for item in response.json()]
