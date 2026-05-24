"""Provider-agnostic LLM helpers. The single import surface for every
agent node + the planner + the summariser.

Two helpers cover all current call sites:

  chat_structured(messages, response_model, ...) -> response_model
      Equivalent to Azure's `client.beta.chat.completions.parse(
      response_format=Model)`. Used by planner + the 6 structured-output
      agents (compliance, data_query, listing, lead_triage, general,
      market_watch's structured variant).

  chat_text(messages, ...) -> str
      Equivalent to Azure's `client.chat.completions.create(...)
      .choices[0].message.content`. Used by summariser + market_watch's
      synthesis step.

Provider selection is driven by `settings.llm_provider`:

  azure   -> openai SDK pointed at Azure AI Foundry v1 endpoint
  bedrock -> AWS Bedrock converse() with forced tool use

Embeddings are not abstracted yet -- the parquet corpora were built with
text-embedding-3-small, so all embed calls still go through Azure
regardless of `llm_provider`. Swapping the embedding model means
rebuilding the corpora (separate workstream).
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from src.app.services import bedrock_chat
from src.app.services.ai_client import chat_model, get_openai_client
from src.settings import settings

M = TypeVar("M", bound=BaseModel)


def chat_structured(
    messages: list[dict[str, str]],
    response_model: type[M],
    *,
    model: str | None = None,
    temperature: float = 0.0,
) -> M:
    """Structured-output chat. Returns a validated instance of response_model."""
    if settings.llm_provider == "bedrock":
        return bedrock_chat.chat_structured(
            messages, response_model, model=model, temperature=temperature
        )

    client = get_openai_client()
    completion = client.beta.chat.completions.parse(
        model=model or chat_model(),
        messages=messages,
        response_format=response_model,
        temperature=temperature,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise ValueError(f"{response_model.__name__} LLM returned no parsed payload")
    return parsed


def chat_text(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.0,
) -> str:
    """Plain-text chat. Returns the content of the first choice."""
    if settings.llm_provider == "bedrock":
        return bedrock_chat.chat_text(messages, model=model, temperature=temperature)

    client = get_openai_client()
    completion = client.chat.completions.create(
        model=model or chat_model(),
        messages=messages,
        temperature=temperature,
    )
    return completion.choices[0].message.content or ""
