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

    # ---- LLM + embedding providers -------------------------------------
    # "openai" (default): any OpenAI-compatible endpoint. The deployment
    #   uses Azure OpenAI's /openai/v1 surface (gpt-4.1-mini +
    #   text-embedding-3-small on the demo's own Azure subscription).
    # "bedrock": the original AWS deployment path (kept as reference;
    #   needs AWS credentials + the boto3 extra).
    llm_provider: str = "openai"
    embed_provider: str = "openai"

    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_chat_model: str = "gpt-4-1-mini"
    llm_embed_model: str = "text-embedding-3-small"
    embed_dim: int = 1536  # text-embedding-3-small; Titan v2 was 1024.
    # NOTE: switching embed provider/model requires REBUILDING the RAG
    # parquets (scripts/build_regulation_corpus.py + build_review_embeddings.py)
    # so corpus and query vectors come from the same model.

    # Legacy Bedrock path (unused unless *_provider == "bedrock").
    aws_region: str = "ap-southeast-2"
    bedrock_chat_model: str = "au.anthropic.claude-sonnet-4-6"
    bedrock_embed_model: str = "amazon.titan-embed-text-v2:0"

    # ---- Artefact store (trained model + RAG parquets) -----------------
    # Azure: public-read blob container base URL, e.g.
    #   https://<account>.blob.core.windows.net/artefacts
    # Backend downloads on boot if files are missing locally.
    artefact_base_url: str = ""
    # Legacy AWS path (unused on Azure).
    s3_artefact_bucket: str = ""

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
