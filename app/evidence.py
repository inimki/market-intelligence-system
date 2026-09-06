import json
from pathlib import Path

from app.normalization import make_content_hash
from app.schemas import CollectedDocument


class EvidenceStore:
    """Persist raw collection evidence separately from normalized database rows."""

    def __init__(self, raw_dir: Path):
        self.raw_dir = raw_dir
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def save(self, run_id: int, document: CollectedDocument) -> Path:
        fingerprint = make_content_hash(
            document.title, f"{document.source_url}\n{document.content}"
        )[:12]
        run_dir = self.raw_dir / f"run-{run_id:04d}"
        run_dir.mkdir(parents=True, exist_ok=True)
        stem = f"{fingerprint}"
        metadata_path = run_dir / f"{stem}.json"
        payload = document.model_dump(mode="json", exclude={"raw_html"})
        metadata_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if document.raw_html:
            (run_dir / f"{stem}.html").write_text(document.raw_html, encoding="utf-8")
        return metadata_path
