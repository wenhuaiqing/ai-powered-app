"""AWS Bedrock chat client. Mirrors the structured-output + plain-text
shape exposed by the Azure path in services/llm.py.

Bedrock's `converse` API takes one or more system blocks, a list of
user/assistant messages, and an inferenceConfig. Tool-use is the
recommended structured-output pattern with Claude: declare a single
tool whose `input_schema` is the desired Pydantic shape, set
`toolChoice.tool.name = <that tool>`, and the model is forced to call
it. The tool's `input` is then guaranteed JSON matching the schema.

We use that pattern. Falls back to JSON-mode prompting on tool-use
failure (rare).
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from src.settings import settings

log = logging.getLogger(__name__)

M = TypeVar("M", bound=BaseModel)


@lru_cache(maxsize=1)
def _client():
    # Imported lazily so users on the Azure path don't need boto3 wired
    # up to run unit tests. boto3 is a heavy import.
    import boto3
    return boto3.client("bedrock-runtime", region_name=settings.aws_region)


def _split_messages(messages: list[dict[str, str]]) -> tuple[list[dict], list[dict]]:
    """Pull `system` messages out into the system block list; everything
    else (user / assistant) becomes a converse message with the [{"text": ...}]
    content shape Bedrock expects.

    Appends a `cachePoint` after the system blocks so the prompt cache
    captures everything up to (but not including) the user message.
    Subsequent calls inside the 5-minute TTL window pay ~10% of the input
    token cost for the cached portion. Each agent's SYSTEM_PROMPT is
    static and 50-150 lines, which is exactly the shape this helps.
    """
    system_blocks: list[dict[str, Any]] = []
    converse: list[dict[str, Any]] = []
    for m in messages:
        role = m["role"]
        content = m["content"]
        if role == "system":
            system_blocks.append({"text": content})
            continue
        converse.append({
            "role": "user" if role == "user" else "assistant",
            "content": [{"text": content}],
        })
    if system_blocks:
        system_blocks.append({"cachePoint": {"type": "default"}})
    return system_blocks, converse


def chat_structured(
    messages: list[dict[str, str]],
    response_model: type[M],
    *,
    model: str | None = None,
    temperature: float = 0.0,
) -> M:
    """Bedrock structured output via forced tool use.

    Equivalent to Azure's `client.beta.chat.completions.parse(response_format=Model)`.
    """
    system_blocks, converse = _split_messages(messages)

    schema = response_model.model_json_schema()
    tool_name = "emit_structured_output"
    tool_config = {
        "tools": [{
            "toolSpec": {
                "name": tool_name,
                "description": f"Emit the response as a {response_model.__name__} object.",
                "inputSchema": {"json": schema},
            }
        }],
        "toolChoice": {"tool": {"name": tool_name}},
    }

    response = _client().converse(
        modelId=model or settings.bedrock_chat_model,
        system=system_blocks,
        messages=converse,
        inferenceConfig={"temperature": temperature, "maxTokens": 4096},
        toolConfig=tool_config,
    )

    payload = _extract_tool_input(response, tool_name)
    try:
        return response_model.model_validate(payload)
    except ValidationError:
        log.warning("Bedrock tool output failed validation, raising for retry", exc_info=True)
        raise


def chat_text(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.0,
) -> str:
    """Plain-text completion via Bedrock converse. Equivalent to
    Azure's `client.chat.completions.create(...).choices[0].message.content`."""
    system_blocks, converse = _split_messages(messages)
    response = _client().converse(
        modelId=model or settings.bedrock_chat_model,
        system=system_blocks,
        messages=converse,
        inferenceConfig={"temperature": temperature, "maxTokens": 4096},
    )
    blocks = response.get("output", {}).get("message", {}).get("content", [])
    for b in blocks:
        if "text" in b:
            return b["text"]
    return ""


def _extract_tool_input(response: dict[str, Any], tool_name: str) -> dict[str, Any]:
    blocks = response.get("output", {}).get("message", {}).get("content", [])
    for b in blocks:
        tu = b.get("toolUse")
        if tu and tu.get("name") == tool_name:
            return tu.get("input", {})
    # Fallback: model returned plain text instead of using the tool.
    # Try to parse it as JSON.
    for b in blocks:
        if "text" in b:
            try:
                return json.loads(b["text"])
            except json.JSONDecodeError:
                continue
    raise RuntimeError(f"Bedrock response contained no tool-use block named {tool_name}")
