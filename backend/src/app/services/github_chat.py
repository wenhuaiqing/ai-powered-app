"""GitHub Models chat client (OpenAI-compatible API, free rate-limited tier).

Mirrors the structured-output + plain-text shape of bedrock_chat so the
llm.py dispatcher can swap providers with a settings flag.

Structured outputs use the same pattern as the Bedrock path: declare a
single tool whose parameters schema is the Pydantic model's JSON schema,
force the model to call it via tool_choice, and validate the arguments.
Falls back to JSON-mode prompting if the tool call comes back malformed.

Auth is a GitHub token with the `models: read` permission:
  - locally / in Azure: a fine-grained PAT in GITHUB_MODELS_TOKEN
  - in GitHub Actions: the built-in GITHUB_TOKEN works (permissions:
    models: read), so CI needs no extra secret.

Free-tier rate limits are real (per-minute and per-day, tiered by
model). A 429 raises like any other failure -- callers already degrade:
the planner falls back to keyword routing, agent nodes append NodeError
and the run continues. That is the demo's rate-limit safety net.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from src.settings import settings

log = logging.getLogger(__name__)

M = TypeVar("M", bound=BaseModel)


@lru_cache(maxsize=1)
def _client():
    # Lazy import; openai is already a backend dependency.
    from openai import OpenAI
    return OpenAI(
        base_url=settings.github_models_base_url,
        api_key=settings.github_models_token,
    )


def _tool_name(response_model: type[BaseModel]) -> str:
    return f"emit_{response_model.__name__.lower()}"


def chat_structured(
    messages: list[dict[str, str]],
    response_model: type[M],
    *,
    model: str | None = None,
    temperature: float = 0.0,
) -> M:
    """Structured output via forced tool call. Returns a validated model."""
    schema = response_model.model_json_schema()
    name = _tool_name(response_model)
    completion = _client().chat.completions.create(
        model=model or settings.github_chat_model,
        messages=messages,
        temperature=temperature,
        tools=[{
            "type": "function",
            "function": {
                "name": name,
                "description": f"Emit a {response_model.__name__} object.",
                "parameters": schema,
            },
        }],
        tool_choice={"type": "function", "function": {"name": name}},
    )
    msg = completion.choices[0].message
    if msg.tool_calls:
        raw = msg.tool_calls[0].function.arguments
        try:
            return response_model.model_validate_json(raw)
        except ValidationError:
            log.warning("Tool-call args failed validation; retrying JSON mode")
    return _chat_structured_json_fallback(
        messages, response_model, model=model, temperature=temperature
    )


def _chat_structured_json_fallback(
    messages: list[dict[str, str]],
    response_model: type[M],
    *,
    model: str | None = None,
    temperature: float = 0.0,
) -> M:
    """Fallback: ask for raw JSON matching the schema and validate it."""
    schema = json.dumps(response_model.model_json_schema())
    augmented = list(messages) + [{
        "role": "user",
        "content": (
            "Respond ONLY with a JSON object that validates against this "
            f"JSON schema (no prose, no code fences):\n{schema}"
        ),
    }]
    completion = _client().chat.completions.create(
        model=model or settings.github_chat_model,
        messages=augmented,
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    content = completion.choices[0].message.content or ""
    return response_model.model_validate_json(content)


def chat_text(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.0,
) -> str:
    """Plain-text chat completion."""
    completion = _client().chat.completions.create(
        model=model or settings.github_chat_model,
        messages=messages,
        temperature=temperature,
    )
    return completion.choices[0].message.content or ""
