"""Provider-agnostic LLM helpers. AWS Bedrock-backed.

Two helpers cover every call site:

  chat_structured(messages, response_model, ...) -> response_model
      Forced tool-use under the hood so the response is guaranteed
      to validate against the Pydantic model.

  chat_text(messages, ...) -> str
      Plain-text completion -- used by Summariser + Market Watch.

Static system prompts (each agent's SYSTEM_PROMPT) get cached on the
Bedrock side via `cachePoint` -- see services/bedrock_chat.py.

Embeddings live in services/embed.py (Bedrock Titan v2).
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from src.app.services import bedrock_chat

M = TypeVar("M", bound=BaseModel)


def chat_structured(
    messages: list[dict[str, str]],
    response_model: type[M],
    *,
    model: str | None = None,
    temperature: float = 0.0,
) -> M:
    """Structured-output chat. Returns a validated instance of response_model."""
    return bedrock_chat.chat_structured(
        messages, response_model, model=model, temperature=temperature
    )


def chat_text(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.0,
) -> str:
    """Plain-text chat. Returns the content of the first choice."""
    return bedrock_chat.chat_text(messages, model=model, temperature=temperature)
