from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    vault_path: Path
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4-mini"
    openai_realtime_model: str = "gpt-realtime-mini"
    openai_realtime_voice: str = "marin"
    db_path: Path = Path("data/mistakes.db")


@lru_cache
def get_settings() -> Settings:
    return Settings()
