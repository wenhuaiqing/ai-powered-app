"""Application settings loaded from environment / .env file."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[REPO_ROOT / ".env", BACKEND_ROOT / ".env"],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM provider toggle. "azure" uses Azure OpenAI for chat; "bedrock"
    # uses AWS Bedrock (Claude on AWS). Embeddings always use Azure for
    # now -- the RAG parquet files were built with text-embedding-3-small,
    # and switching to Titan would mean rebuilding the corpora.
    llm_provider: Literal["azure", "bedrock"] = "azure"

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_chat_model: str = "gpt-4o"
    azure_openai_embed_model: str = "text-embedding-3-small"

    # AWS Bedrock (only used when LLM_PROVIDER=bedrock).
    aws_region: str = "ap-southeast-2"
    bedrock_chat_model: str = "anthropic.claude-sonnet-4-6-20250930-v1:0"

    # Tavily
    tavily_api_key: str = ""

    # Data paths
    data_dir: Path = REPO_ROOT / "data"
    model_path: Path = REPO_ROOT / "data" / "model.pkl"
    duckdb_path: Path = REPO_ROOT / "data" / "platform.duckdb"

    # MySQL (OLTP). Defaults match docker-compose.yml.
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "app"
    mysql_password: str = "app"
    mysql_database: str = "reapit_demo"

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            "?charset=utf8mb4"
        )

    # CORS
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
