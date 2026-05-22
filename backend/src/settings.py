"""Application settings loaded from environment / .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[REPO_ROOT / ".env", BACKEND_ROOT / ".env"],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_chat_model: str = "gpt-4o"
    azure_openai_embed_model: str = "text-embedding-3-small"

    # Tavily
    tavily_api_key: str = ""

    # Data paths
    data_dir: Path = REPO_ROOT / "data"
    model_path: Path = REPO_ROOT / "data" / "model.pkl"
    duckdb_path: Path = REPO_ROOT / "data" / "platform.duckdb"

    # CORS
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
