"""Provider-agnostic LLM helpers.

Two helpers cover every call site:

  chat_structured(messages, response_model, ...) -> response_model
      Forced tool-use under the hood so the response is guaranteed
      to validate against the Pydantic model.

  chat_text(messages, ...) -> str
      Plain-text completion -- used by Summariser + Market Watch.

The provider is chosen by settings.llm_provider:
  "github"  -> GitHub Models (OpenAI-compatible, free rate-limited tier)
  "bedrock" -> AWS Bedrock converse (the original AWS deployment path)

Embeddings live in services/embed.py with the same provider flag.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from src.settings import settings

M = TypeVar("M", bound=BaseModel)


def _backend():
    if settings.llm_provider == "bedrock":
        from src.app.services import bedrock_chat
        return bedrock_chat
    from src.app.services import github_chat
    return github_chat


def chat_structured(
    messages: list[dict[str, str]],
    response_model: type[M],
    *,
    model: str | None = None,
    temperature: float = 0.0,
) -> M:
    """Structured-output chat. Returns a validated instance of response_model."""
    return _backend().chat_structured(
        messages, response_model, model=model, temperature=temperature
    )


def chat_text(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.0,
) -> str:
    """Plain-text chat. Returns the content of the first choice."""
    return _backend().chat_text(messages, model=model, temperature=temperature)
