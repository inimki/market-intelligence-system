from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.analysis import AnalysisResult
from app.presentation import format_beijing_time
from app.schemas import IntelItem


class HtmlReportGenerator:
    def __init__(self, report_dir: Path):
        template_dir = Path(__file__).parent / "templates"
        self.environment = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self.environment.filters["beijing_time"] = format_beijing_time
        self.report_dir = report_dir
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        run_id: int,
        items: list[IntelItem],
        analysis: AnalysisResult,
        title: str | None = None,
        scope: dict[str, object] | None = None,
    ) -> Path:
        template = self.environment.get_template("report.html.j2")
        generated_at = datetime.now(ZoneInfo("Asia/Shanghai"))
        filename = f"market-intelligence-run-{run_id:04d}.html"
        output_path = self.report_dir / filename
        output_path.write_text(
            template.render(
                run_id=run_id,
                generated_at=generated_at,
                items=items,
                analysis=analysis,
                report_title=title or "市场情报自动报告",
                report_scope=scope,
            ),
            encoding="utf-8",
        )
        return output_path
