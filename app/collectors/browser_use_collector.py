import json
import os

from app.collectors.base import BaseCollector, CollectorError
from app.schemas import CollectedDocument, SourceConfig


class BrowserUseCollector(BaseCollector):
    def __init__(
        self,
        browser_use_api_key: str | None = None,
        ai_api_key: str | None = None,
        ai_provider: str = "deepseek",
        ai_base_url: str | None = None,
        ai_model: str = "deepseek-v4-flash",
    ):
        self.browser_use_api_key = browser_use_api_key or os.getenv("BROWSER_USE_API_KEY")
        self.ai_api_key = ai_api_key or os.getenv("AI_API_KEY")
        self.ai_provider = ai_provider.strip().lower()
        self.ai_base_url = ai_base_url
        self.ai_model = ai_model

    def _build_llm(self):
        from browser_use import ChatBrowserUse, ChatOpenAI

        if self.browser_use_api_key:
            return ChatBrowserUse(
                model="bu-2-0-mini-preview",
                api_key=self.browser_use_api_key,
            )
        if not self.ai_api_key:
            raise CollectorError(
                "Browser Use 需要 AI_API_KEY；也可以单独配置 BROWSER_USE_API_KEY"
            )
        if self.ai_provider == "deepseek":
            # DeepSeek's thinking mode rejects forced tool_choice. Browser Use can
            # instead put its output schema in the system prompt and validate the
            # returned JSON locally, which stays compatible with the official
            # OpenAI-style DeepSeek endpoint.
            return ChatOpenAI(
                model=self.ai_model,
                api_key=self.ai_api_key,
                base_url=self.ai_base_url or "https://api.deepseek.com",
                temperature=0,
                frequency_penalty=None,
                reasoning_effort=None,
                max_completion_tokens=None,
                add_schema_to_system_prompt=True,
                dont_force_structured_output=True,
                remove_min_items_from_schema=True,
                remove_defaults_from_schema=True,
            )
        return ChatOpenAI(
            model=self.ai_model,
            api_key=self.ai_api_key,
            base_url=self.ai_base_url,
            temperature=0,
            reasoning_effort=None,
        )

    async def collect(self, source: SourceConfig) -> list[CollectedDocument]:
        try:
            from browser_use import Agent, BrowserProfile
        except ImportError as exc:
            raise CollectorError(
                "Browser Use 未安装。请执行 pip install -e '.[collectors]' 后重试。"
            ) from exc

        hint = source.extraction_hint or "提取页面主标题、正文和发布时间"
        task = f"""
只允许访问 {source.url.host} 域名。打开 {source.url}，{hint}。
不要提交表单、购买、发布内容或修改账户。最多完成 10 个操作。
最终只返回一个 JSON 对象：
{{"title":"...","content":"...","published_at":null,"author":null,"final_url":"..."}}
""".strip()
        try:
            agent = Agent(
                task=task,
                llm=self._build_llm(),
                browser_profile=BrowserProfile(
                    headless=True,
                    allowed_domains=[source.url.host],
                    block_ip_addresses=True,
                    accept_downloads=False,
                    # These convenience extensions are unnecessary for a
                    # read-only extraction task. Disabling them avoids a slow
                    # first-run download and keeps the browser launch within
                    # Browser Use's startup timeout.
                    enable_default_extensions=False,
                    captcha_solver=False,
                ),
                max_steps=10,
                use_vision=False,
                use_thinking=False,
            )
            history = await agent.run()
            raw_result = history.final_result()
        except Exception as exc:
            raise CollectorError(f"Browser Use 执行失败: {exc}") from exc

        if not raw_result:
            raise CollectorError("Browser Use 没有返回最终结果")
        try:
            payload = json.loads(raw_result)
        except json.JSONDecodeError as exc:
            raise CollectorError("Browser Use 返回内容不是约定的 JSON") from exc

        return [
            CollectedDocument(
                source_name=source.name,
                source_url=source.url,
                final_url=payload.get("final_url") or source.url,
                title=payload.get("title") or source.name,
                content=payload.get("content") or "",
                published_at=payload.get("published_at"),
                author=payload.get("author"),
                metadata={
                    "collector": "browser-use",
                    "step_count": len(history.history),
                    "source_tags": source.tags,
                },
            )
        ]
