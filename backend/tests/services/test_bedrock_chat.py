"""Bedrock chat client tests. boto3 client is mocked.

We're verifying:
  - chat_structured() forces tool-use and pulls the schema from the
    Pydantic model
  - the tool's input JSON is validated back into the model
  - chat_text() extracts text blocks from the converse response
  - system messages are split out into Bedrock's separate `system` arg
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from src.app.services import bedrock_chat


class _Score(BaseModel):
    text: str
    score: int


def _fake_converse_with_tool(payload: dict) -> MagicMock:
    """Build a converse-shaped response with one toolUse block."""
    return {
        "output": {
            "message": {
                "content": [{
                    "toolUse": {
                        "name": "emit_structured_output",
                        "input": payload,
                    }
                }]
            }
        }
    }


def _fake_converse_with_text(text: str) -> dict:
    return {
        "output": {
            "message": {
                "content": [{"text": text}]
            }
        }
    }


def test_structured_returns_parsed_model_from_tool_input():
    fake_client = MagicMock()
    fake_client.converse.return_value = _fake_converse_with_tool({"text": "hello", "score": 9})

    with patch.object(bedrock_chat, "_client", return_value=fake_client):
        result = bedrock_chat.chat_structured(
            messages=[
                {"role": "system", "content": "be terse"},
                {"role": "user", "content": "hi"},
            ],
            response_model=_Score,
        )

    assert result == _Score(text="hello", score=9)

    # System messages get split into the system arg; user/assistant go in messages.
    # A cachePoint is appended after the system text so Bedrock caches the
    # static system prompt across calls (5-min TTL).
    call_kwargs = fake_client.converse.call_args.kwargs
    assert call_kwargs["system"] == [
        {"text": "be terse"},
        {"cachePoint": {"type": "default"}},
    ]
    assert call_kwargs["messages"] == [{
        "role": "user",
        "content": [{"text": "hi"}],
    }]

    # Tool-use must be forced (choice = the specific tool).
    tool_config = call_kwargs["toolConfig"]
    assert tool_config["toolChoice"]["tool"]["name"] == "emit_structured_output"
    # Schema is the Pydantic model's JSON schema.
    assert tool_config["tools"][0]["toolSpec"]["inputSchema"]["json"]["properties"]


def test_structured_falls_back_to_json_text_when_no_tool_use():
    """If the model ignored tool-use and returned plain JSON text,
    we should still parse it."""
    fake_client = MagicMock()
    fake_client.converse.return_value = _fake_converse_with_text('{"text":"x","score":3}')

    with patch.object(bedrock_chat, "_client", return_value=fake_client):
        result = bedrock_chat.chat_structured(
            messages=[{"role": "user", "content": "hi"}],
            response_model=_Score,
        )

    assert result == _Score(text="x", score=3)


def test_structured_raises_on_invalid_payload():
    fake_client = MagicMock()
    fake_client.converse.return_value = _fake_converse_with_tool({"text": "hi"})  # missing score

    with patch.object(bedrock_chat, "_client", return_value=fake_client):
        with pytest.raises(Exception):
            bedrock_chat.chat_structured(
                messages=[{"role": "user", "content": "hi"}],
                response_model=_Score,
            )


def test_chat_text_returns_first_text_block():
    fake_client = MagicMock()
    fake_client.converse.return_value = _fake_converse_with_text("the answer")

    with patch.object(bedrock_chat, "_client", return_value=fake_client):
        out = bedrock_chat.chat_text(
            messages=[
                {"role": "system", "content": "be brief"},
                {"role": "user", "content": "?"},
            ],
        )

    assert out == "the answer"
    call_kwargs = fake_client.converse.call_args.kwargs
    assert "toolConfig" not in call_kwargs  # plain text path
    assert call_kwargs["system"] == [
        {"text": "be brief"},
        {"cachePoint": {"type": "default"}},
    ]


def test_no_cache_point_when_there_are_no_system_messages():
    """If the caller passes only user messages (no system), don't append
    a cachePoint -- it would attempt to cache an empty prefix."""
    fake_client = MagicMock()
    fake_client.converse.return_value = _fake_converse_with_text("ok")

    with patch.object(bedrock_chat, "_client", return_value=fake_client):
        bedrock_chat.chat_text(messages=[{"role": "user", "content": "?"}])

    call_kwargs = fake_client.converse.call_args.kwargs
    assert call_kwargs["system"] == []
