"""OpenAI-compatible chat client (Azure OpenAI via its /openai/v1 surface,

or any endpoint speaking the OpenAI protocol). Mirrors the
structured-output + plain-text shape of bedrock_chat so the llm.py
dispatcher can swap providers with a settings flag.

Structured outputs use the same pattern as the Bedrock path: declare a
single tool whose parameters schema is the Pydantic model's JSON schema,
force the model to call it via tool_choice, and validate the arguments.
Falls back to JSON-mode prompting if the tool call comes back malformed.

Configuration (settings / env):
  LLM_BASE_URL    e.g. https://<resource>.openai.azure.com/openai/v1/
  LLM_API_KEY     the endpoint's API key
  LLM_CHAT_MODEL  deployment/model name (e.g. gpt-4-1-mini)

Any 429/5xx raises like any other failure -- callers already degrade:
the planner falls back to keyword routing, agent nodes append NodeError
and the run continues. Graceful degradation is the demo's safety net.
"""

from __future__ import annotations

import json
import logging
import re
import time
from functools import lru_cache
from typing import Any, Callable, TypeVar

from pydantic import BaseModel, ValidationError

from src.settings import settings

log = logging.getLogger(__name__)

M = TypeVar("M", bound=BaseModel)


@lru_cache(maxsize=1)
def _client():
    # Lazy import; openai is already a backend dependency.
    from openai import OpenAI
    return OpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
    )


# A node has a 30s budget (see the LangGraph harness), so a retry is
# only worth attempting when the provider asks for a short wait.
_MAX_RATE_LIMIT_RETRIES = 2
_MAX_RATE_LIMIT_WAIT = 5.0


def _retry_after_seconds(exc: Exception) -> float | None:
    """Seconds the provider asked us to wait, or None if it didn't say."""
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            header = response.headers.get("retry-after")
        except Exception:  # noqa: BLE001 - header access varies by transport
            header = None
        if header:
            try:
                return float(header)
            except ValueError:
                pass
    # Gemini reports it in the body rather than a header.
    match = re.search(r"'retryDelay': '(\d+(?:\.\d+)?)s'", str(exc))
    return float(match.group(1)) if match else None


def _with_rate_limit_retry(call: Callable[[], Any]) -> Any:
    """Run `call`, retrying briefly on 429.

    Free-tier endpoints meter per minute and the graph is sequential, so
    going over is usually a matter of a call or two -- a short wait
    clears it. A long wait cannot be honoured: exceeding the node budget
    turns a recoverable blip into a timeout, so we give up and let the
    caller degrade, which it already knows how to do.
    """
    from openai import RateLimitError

    for attempt in range(_MAX_RATE_LIMIT_RETRIES + 1):
        try:
            return call()
        except RateLimitError as exc:
            wait = _retry_after_seconds(exc)
            if attempt == _MAX_RATE_LIMIT_RETRIES or (wait or 0) > _MAX_RATE_LIMIT_WAIT:
                log.warning(
                    "rate limited (provider asked for %s); giving up after %d attempt(s)",
                    f"{wait:.0f}s" if wait else "no delay",
                    attempt + 1,
                )
                raise
            delay = wait if wait is not None else 2.0
            log.info("rate limited; retrying in %.1fs", delay)
            time.sleep(delay)


def _tool_name(response_model: type[BaseModel]) -> str:
    return f"emit_{response_model.__name__.lower()}"


def _inline_defs(schema: dict[str, Any]) -> dict[str, Any]:
    """Return an equivalent schema with `$defs`/`$ref` inlined.

    Pydantic hoists nested models into `$defs` and points at them with
    `$ref`. Azure OpenAI resolves those; other OpenAI-compatible layers
    (Gemini's among them) reject refs inside a tool's parameters schema.
    A rejection is an API error, which is raised before the JSON-mode
    fallback below can catch it, so the planner would fail outright
    rather than degrade. Inlining keeps one code path valid everywhere.
    """
    defs = schema.get("$defs", {})

    def resolve(node: Any, seen: frozenset[str]) -> Any:
        if isinstance(node, list):
            return [resolve(n, seen) for n in node]
        if not isinstance(node, dict):
            return node
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            key = ref.rsplit("/", 1)[-1]
            if key not in defs or key in seen:
                # Missing or self-referential: an open object beats a loop.
                return {"type": "object"}
            target = resolve(defs[key], seen | {key})
            siblings = {k: v for k, v in node.items() if k != "$ref"}
            return {**target, **siblings} if siblings else target
        return {k: resolve(v, seen) for k, v in node.items() if k != "$defs"}

    return resolve(schema, frozenset())


def chat_structured(
    messages: list[dict[str, str]],
    response_model: type[M],
    *,
    model: str | None = None,
    temperature: float = 0.0,
) -> M:
    """Structured output via forced tool call. Returns a validated model."""
    schema = _inline_defs(response_model.model_json_schema())
    name = _tool_name(response_model)
    completion = _with_rate_limit_retry(lambda: _client().chat.completions.create(
        model=model or settings.llm_chat_model,
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
    ))
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
    schema = json.dumps(_inline_defs(response_model.model_json_schema()))
    augmented = list(messages) + [{
        "role": "user",
        "content": (
            "Respond ONLY with a JSON object that validates against this "
            f"JSON schema (no prose, no code fences):\n{schema}"
        ),
    }]
    completion = _with_rate_limit_retry(lambda: _client().chat.completions.create(
        model=model or settings.llm_chat_model,
        messages=augmented,
        temperature=temperature,
        response_format={"type": "json_object"},
    ))
    content = completion.choices[0].message.content or ""
    return response_model.model_validate_json(content)


def chat_text(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.0,
) -> str:
    """Plain-text chat completion."""
    completion = _with_rate_limit_retry(lambda: _client().chat.completions.create(
        model=model or settings.llm_chat_model,
        messages=messages,
        temperature=temperature,
    ))
    return completion.choices[0].message.content or ""
