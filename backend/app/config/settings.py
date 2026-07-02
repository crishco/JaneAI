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

    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size_words: int = 500
    chunk_overlap_words: int = 50
    retrieval_top_k: int = 5

    upload_directory: str = "./data/uploads"
    upload_max_file_size_mb: int = 25
    allowed_upload_extensions: tuple[str, ...] = (
        ".pdf",
        ".docx",
        ".txt",
        ".md",
        ".markdown",
    )

    log_level: str = "INFO"
    log_format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
