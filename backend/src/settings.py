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

    # AWS Bedrock is the only chat + embed provider. (Azure OpenAI was
    # the dev path during Phase 1; Phase 2 step 6 removed it -- the eval
    # judge in evals/judge.py still imports openai for its own scoring
    # workflow, that's a separate dev-only tool.)
    # The model ID is a cross-region inference profile -- prefix tells
    # Bedrock which geo to route through:
    #   au. -> ap-southeast-2 (Sydney)
    #   us. -> us-east-1 / us-west-2
    #   eu. -> eu-* regions
    # The bare ID `anthropic.claude-sonnet-4-6` is in-region only and
    # may not be deployed in every region; the cross-region profile is
    # the recommended default.
    aws_region: str = "ap-southeast-2"
    bedrock_chat_model: str = "au.anthropic.claude-sonnet-4-6"
    bedrock_embed_model: str = "amazon.titan-embed-text-v2:0"
    embed_dim: int = 1024  # Titan v2 default; 256 + 512 also valid

    # S3 bucket holding the trained model + RAG embedding parquets.
    # Backend downloads on boot if these files are missing locally.
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
