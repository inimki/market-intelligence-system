import re
from collections import Counter
from dataclasses import dataclass

import pandas as pd

from app.schemas import IntelItem

STOP_WORDS = {
    "一个",
    "以及",
    "同时",
    "进行",
    "相关",
    "计划",
    "表示",
    "公司",
    "正在",
    "提供",
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
}


@dataclass
class AnalysisResult:
    total_items: int
    source_count: int
    newest_at: str | None
    items_by_source: list[dict]
    items_by_day: list[dict]
    top_keywords: list[dict]
    highlights: list[str]


class DeterministicAnalyzer:
    def analyze(self, items: list[IntelItem]) -> AnalysisResult:
        if not items:
            return AnalysisResult(0, 0, None, [], [], [], ["本次没有可分析的新情报。"])

        rows = [
            {
                "source": item.source_name,
                "published_at": item.published_at or item.collected_at,
                "title": item.title,
                "content": item.content,
            }
            for item in items
        ]
        frame = pd.DataFrame(rows)
        frame["published_at"] = pd.to_datetime(frame["published_at"], utc=True)
        frame["day"] = frame["published_at"].dt.strftime("%Y-%m-%d")

        by_source = (
            frame.groupby("source", dropna=False)
            .size()
            .sort_values(ascending=False)
            .rename("count")
            .reset_index()
            .to_dict("records")
        )
        by_day = (
            frame.groupby("day")
            .size()
            .rename("count")
            .reset_index()
            .sort_values("day")
            .to_dict("records")
        )
        keywords = self._keywords(" ".join(frame["title"] + " " + frame["content"]))
        highlights = [
            f"本期共收录 {len(items)} 条去重后的情报，来自 {frame['source'].nunique()} 个信源。",
            f"信息量最多的信源是“{by_source[0]['source']}”，共 {by_source[0]['count']} 条。",
        ]
        if keywords:
            highlights.append(
                "高频主题包括：" + "、".join(keyword["keyword"] for keyword in keywords[:5]) + "。"
            )
        return AnalysisResult(
            total_items=len(items),
            source_count=int(frame["source"].nunique()),
            newest_at=frame["published_at"].max().isoformat(),
            items_by_source=by_source,
            items_by_day=by_day,
            top_keywords=keywords,
            highlights=highlights,
        )

    @staticmethod
    def _keywords(text: str, limit: int = 12) -> list[dict]:
        import jieba

        chinese_tokens = [
            token.strip().lower()
            for token in jieba.lcut(text)
            if len(token.strip()) >= 2 and re.fullmatch(r"[\u4e00-\u9fff]+", token.strip())
        ]
        english_tokens = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", text.lower())
        counts = Counter(
            token for token in [*chinese_tokens, *english_tokens] if token not in STOP_WORDS
        )
        return [{"keyword": word, "count": count} for word, count in counts.most_common(limit)]


class PandasAIAnalyzer:
    """Optional exploratory analysis. It never replaces deterministic report metrics."""

    def __init__(
        self,
        api_key: str,
        model: str,
        provider: str = "deepseek",
        api_base: str | None = None,
    ):
        self.api_key = api_key
        self.model = model
        self.provider = provider.strip().lower()
        self.api_base = api_base

    def _litellm_model(self) -> str:
        if "/" in self.model:
            return self.model
        if self.provider in {"deepseek", "openai", "anthropic", "gemini"}:
            return f"{self.provider}/{self.model}"
        return self.model

    def _litellm_options(self) -> dict:
        options: dict = {
            "api_key": self.api_key,
            "timeout": 90,
        }
        if self.api_base:
            options["api_base"] = self.api_base
        # DeepSeek currently enables thinking by default. PandasAI needs the generated
        # code in message.content, so use non-thinking mode for this integration.
        if self.provider == "deepseek":
            options["extra_body"] = {"thinking": {"type": "disabled"}}
        return options

    def ask(self, items: list[IntelItem], question: str) -> str:
        try:
            import pandasai as pai
            from pandasai_litellm.litellm import LiteLLM
        except ImportError as exc:
            raise RuntimeError("请安装 pip install -e '.[ai]' 后使用 PandasAI") from exc

        frame = pd.DataFrame(
            [
                {
                    "source": item.source_name,
                    "title": item.title,
                    "published_at": item.published_at,
                    "summary": item.summary,
                }
                for item in items
            ]
        )
        llm = LiteLLM(model=self._litellm_model(), **self._litellm_options())
        # The analysis container is intentionally read-only. Keep PandasAI's
        # optional file logger disabled so exploratory questions do not try to
        # create /app/pandasai.log.
        pai.config.set({"llm": llm, "save_logs": False})
        response = pai.DataFrame(frame).chat(question)
        return str(response)
