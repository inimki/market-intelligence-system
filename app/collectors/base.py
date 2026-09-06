from abc import ABC, abstractmethod

from app.schemas import CollectedDocument, SourceConfig


class CollectorError(RuntimeError):
    """A source could not be collected in a controlled way."""


class BaseCollector(ABC):
    @abstractmethod
    async def collect(self, source: SourceConfig) -> list[CollectedDocument]:
        raise NotImplementedError
