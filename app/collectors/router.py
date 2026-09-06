from app.collectors.base import BaseCollector
from app.collectors.browser_use_collector import BrowserUseCollector
from app.collectors.crawl4ai_collector import Crawl4AICollector
from app.collectors.demo import DemoCollector
from app.collectors.remote import RemoteCollector
from app.config import Settings
from app.schemas import SourceConfig, SourceKind


class CollectorRouter:
    def __init__(self, settings: Settings):
        if settings.collector_service_url:
            remote = RemoteCollector(settings.collector_service_url)
            self.collectors: dict[SourceKind, BaseCollector] = {
                SourceKind.DEMO: DemoCollector(),
                SourceKind.STATIC: remote,
                SourceKind.INTERACTIVE: remote,
            }
        else:
            self.collectors = {
                SourceKind.DEMO: DemoCollector(),
                SourceKind.STATIC: Crawl4AICollector(),
                SourceKind.INTERACTIVE: BrowserUseCollector(
                    browser_use_api_key=settings.browser_use_api_key,
                    ai_api_key=settings.ai_api_key or settings.openai_api_key,
                    ai_provider=settings.ai_provider,
                    ai_base_url=settings.ai_base_url,
                    ai_model=settings.ai_model,
                ),
            }

    async def collect(self, source: SourceConfig):
        return await self.collectors[source.kind].collect(source)
