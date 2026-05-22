"""Azure OpenAI client. Same pattern as mcnab-data-app/services/ai/client.py."""

from __future__ import annotations

from functools import lru_cache

from openai import OpenAI

from src.settings import settings


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    """OpenAI-compatible client pointed at Azure AI Foundry."""
    if not settings.azure_openai_endpoint:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT is not configured")
    if not settings.azure_openai_api_key:
        raise RuntimeError("AZURE_OPENAI_API_KEY is not configured")
    return OpenAI(
        base_url=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
    )


def chat_model() -> str:
    return settings.azure_openai_chat_model


def embed_model() -> str:
    return settings.azure_openai_embed_model
