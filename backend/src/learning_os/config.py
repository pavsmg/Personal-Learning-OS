from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    vault_path: Path
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_realtime_model: str = "gpt-realtime-mini"
    openai_realtime_voice: str = "marin"
    # decisions.md #61: whisper-1 (the previous hardcoded default) is the
    # model most prone to hallucinating plausible-but-unrelated phrases on
    # quiet/noisy input, which is what #58's real bad transcript looked
    # like. gpt-4o-mini-transcribe is a newer, less hallucination-prone
    # option -- kept as a setting, not a constant, so it can be A/B'd
    # against real sessions without editing code.
    openai_realtime_transcription_model: str = "gpt-4o-mini-transcribe"
    openai_realtime_silence_duration_ms: int = 800
    openai_realtime_noise_reduction: str = "far_field"
    db_path: Path = Path("data/mistakes.db")
    language_lab_path: Path = Path.home() / "Projects" / "Language-Lab"


@lru_cache
def get_settings() -> Settings:
    return Settings()
