"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for JaneAI."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="JANE_",
        case_sensitive=False,
    )

    app_name: str = "JaneAI"
    app_version: str = "1.0.0"
    debug: bool = False

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    ollama_timeout_seconds: float = 120.0

    database_url: str = "sqlite:///./data/janeai.db"
    database_echo: bool = False

    chroma_persist_directory: str = "./data/chroma"
    chroma_collection_name: str = "janeai_memory"

    log_level: str = "INFO"
    log_format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
