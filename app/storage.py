import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.schemas import IntelItem, RunRecord, SourceConfig, SourceKind


class Base(DeclarativeBase):
    pass


class SourceRow(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(2000), unique=True)
    kind: Mapped[str] = mapped_column(String(32), default=SourceKind.STATIC.value)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    extraction_hint: Mapped[str | None] = mapped_column(Text, nullable=True)


class IntelItemRow(Base):
    __tablename__ = "intel_items"
    __table_args__ = (UniqueConstraint("canonical_url", "content_hash", name="uq_item_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_name: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str] = mapped_column(String(2000))
    url: Mapped[str] = mapped_column(String(2000))
    canonical_url: Mapped[str] = mapped_column(String(2000), index=True)
    title: Mapped[str] = mapped_column(String(1000))
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    author: Mapped[str | None] = mapped_column(String(300), nullable=True)
    keywords_json: Mapped[str] = mapped_column(Text, default="[]")
    entities_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="ok")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")


class RunRow(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running")
    report_path: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    stats_json: Mapped[str] = mapped_column(Text, default="{}")


class Repository:
    def __init__(self, database_url: str):
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine = create_engine(database_url, future=True, connect_args=connect_args)
        self.Session = sessionmaker(self.engine, expire_on_commit=False)

    def init(self) -> None:
        if self.engine.url.get_backend_name() == "sqlite":
            database = self.engine.url.database
            if database and database != ":memory:":
                Path(database).parent.mkdir(parents=True, exist_ok=True)
        Base.metadata.create_all(self.engine)

    def add_source(self, source: SourceConfig) -> SourceConfig:
        with self.Session.begin() as session:
            existing = session.scalar(select(SourceRow).where(SourceRow.url == str(source.url)))
            if existing:
                existing.name = source.name
                existing.kind = source.kind.value
                existing.enabled = source.enabled
                existing.tags_json = json.dumps(source.tags, ensure_ascii=False)
                existing.extraction_hint = source.extraction_hint
                row = existing
            else:
                row = SourceRow(
                    name=source.name,
                    url=str(source.url),
                    kind=source.kind.value,
                    enabled=source.enabled,
                    tags_json=json.dumps(source.tags, ensure_ascii=False),
                    extraction_hint=source.extraction_hint,
                )
                session.add(row)
                session.flush()
            return self._source_from_row(row)

    def list_sources(self, enabled_only: bool = False) -> list[SourceConfig]:
        with self.Session() as session:
            query = select(SourceRow).order_by(SourceRow.id)
            if enabled_only:
                query = query.where(SourceRow.enabled.is_(True))
            return [self._source_from_row(row) for row in session.scalars(query)]

    def disable_other_discovered_sources(self, company: str, keep_url: str) -> None:
        """Disable stale URLs previously auto-discovered for the same company."""
        with self.Session.begin() as session:
            for row in session.scalars(select(SourceRow)):
                tags = json.loads(row.tags_json)
                if row.url != keep_url and company in tags and "自动发现" in tags:
                    row.enabled = False

    def create_run(self) -> int:
        with self.Session.begin() as session:
            row = RunRow(started_at=datetime.now(UTC), status="running")
            session.add(row)
            session.flush()
            return row.id

    def finish_run(self, run_id: int, status: str, stats: dict, report_path: str | None) -> None:
        with self.Session.begin() as session:
            row = session.get(RunRow, run_id)
            if not row:
                raise ValueError(f"run {run_id} not found")
            row.finished_at = datetime.now(UTC)
            row.status = status
            row.stats_json = json.dumps(stats, ensure_ascii=False)
            row.report_path = report_path

    def insert_item(self, item: IntelItem) -> bool:
        try:
            with self.Session.begin() as session:
                exists = session.scalar(
                    select(IntelItemRow).where(
                        IntelItemRow.canonical_url == item.canonical_url,
                        IntelItemRow.content_hash == item.content_hash,
                    )
                )
                if exists:
                    # 清洗和摘要规则升级后，同一正文不应继续保留旧的展示噪声。
                    exists.title = item.title
                    exists.content = item.content
                    exists.summary = item.summary
                    exists.evidence_json = json.dumps(item.evidence, ensure_ascii=False)
                    exists.keywords_json = json.dumps(item.keywords, ensure_ascii=False)
                    exists.entities_json = json.dumps(item.entities, ensure_ascii=False)
                    exists.status = item.status
                    exists.metadata_json = json.dumps(item.metadata, ensure_ascii=False)
                    return False
                session.add(self._row_from_item(item))
            return True
        except IntegrityError:
            return False

    def list_items(self, limit: int = 1000) -> list[IntelItem]:
        with self.Session() as session:
            rows = session.scalars(
                select(IntelItemRow).order_by(IntelItemRow.collected_at.desc()).limit(limit)
            )
            return [self._item_from_row(row) for row in rows]

    def list_runs(self, limit: int = 50) -> list[RunRecord]:
        with self.Session() as session:
            rows = session.scalars(select(RunRow).order_by(RunRow.id.desc()).limit(limit))
            return [
                RunRecord(
                    id=row.id,
                    started_at=row.started_at,
                    finished_at=row.finished_at,
                    status=row.status,
                    report_path=row.report_path,
                    stats=json.loads(row.stats_json),
                )
                for row in rows
            ]

    @staticmethod
    def _source_from_row(row: SourceRow) -> SourceConfig:
        return SourceConfig(
            id=row.id,
            name=row.name,
            url=row.url,
            kind=SourceKind(row.kind),
            enabled=row.enabled,
            tags=json.loads(row.tags_json),
            extraction_hint=row.extraction_hint,
        )

    @staticmethod
    def _row_from_item(item: IntelItem) -> IntelItemRow:
        return IntelItemRow(
            source_name=item.source_name,
            source_url=item.source_url,
            url=item.url,
            canonical_url=item.canonical_url,
            title=item.title,
            content=item.content,
            summary=item.summary,
            published_at=item.published_at,
            collected_at=item.collected_at,
            author=item.author,
            keywords_json=json.dumps(item.keywords, ensure_ascii=False),
            entities_json=json.dumps(item.entities, ensure_ascii=False),
            evidence_json=json.dumps(item.evidence, ensure_ascii=False),
            content_hash=item.content_hash,
            status=item.status,
            metadata_json=json.dumps(item.metadata, ensure_ascii=False),
        )

    @staticmethod
    def _item_from_row(row: IntelItemRow) -> IntelItem:
        return IntelItem(
            id=row.id,
            source_name=row.source_name,
            source_url=row.source_url,
            url=row.url,
            canonical_url=row.canonical_url,
            title=row.title,
            content=row.content,
            summary=row.summary,
            published_at=row.published_at,
            collected_at=row.collected_at,
            author=row.author,
            keywords=json.loads(row.keywords_json),
            entities=json.loads(row.entities_json),
            evidence=json.loads(row.evidence_json),
            content_hash=row.content_hash,
            status=row.status,
            metadata=json.loads(row.metadata_json),
        )
