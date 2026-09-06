from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./data/market_intel.db"
    report_dir: Path = Path("./data/reports")
    raw_dir: Path = Path("./data/raw")
    default_timezone: str = "Asia/Shanghai"
    collector_service_url: str | None = None
    analysis_service_url: str | None = None
    browser_use_api_key: str | None = None
    ai_provider: str = "deepseek"
    ai_api_key: str | None = None
    ai_base_url: str | None = None
    ai_model: str = "deepseek-v4-flash"
    # Backward compatibility for installations that still use the old variable.
    openai_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def ensure_directories(self) -> None:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
