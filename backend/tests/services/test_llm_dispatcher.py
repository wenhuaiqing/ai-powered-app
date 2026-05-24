"""Provider dispatcher tests. Both paths (azure, bedrock) are mocked --
we're checking that the dispatcher routes correctly, not that either
SDK actually works.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from src.app.services import llm


class _Greeting(BaseModel):
    text: str
    confidence: float


# ---- Azure path -------------------------------------------------------------

def test_chat_structured_routes_to_azure_by_default():
    """Default settings.llm_provider is 'azure'. The dispatcher should
    call openai's beta.chat.completions.parse and return the parsed
    response model unchanged."""
    fake_parsed = _Greeting(text="hello", confidence=0.9)
    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock(message=MagicMock(parsed=fake_parsed))]
    fake_client = MagicMock()
    fake_client.beta.chat.completions.parse.return_value = fake_completion

    with patch.object(llm, "get_openai_client", return_value=fake_client):
        result = llm.chat_structured(
            messages=[{"role": "user", "content": "hi"}],
            response_model=_Greeting,
        )

    assert result == fake_parsed
    fake_client.beta.chat.completions.parse.assert_called_once()
    call_kwargs = fake_client.beta.chat.completions.parse.call_args.kwargs
    assert call_kwargs["response_format"] is _Greeting


def test_chat_text_routes_to_azure_by_default():
    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock(message=MagicMock(content="hi back"))]
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_completion

    with patch.object(llm, "get_openai_client", return_value=fake_client):
        text = llm.chat_text(messages=[{"role": "user", "content": "hi"}])

    assert text == "hi back"


def test_chat_structured_raises_when_azure_returns_none():
    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock(message=MagicMock(parsed=None))]
    fake_client = MagicMock()
    fake_client.beta.chat.completions.parse.return_value = fake_completion

    with patch.object(llm, "get_openai_client", return_value=fake_client):
        with pytest.raises(ValueError, match="no parsed payload"):
            llm.chat_structured(
                messages=[{"role": "user", "content": "hi"}],
                response_model=_Greeting,
            )


# ---- Bedrock path -----------------------------------------------------------

def test_chat_structured_routes_to_bedrock_when_provider_is_bedrock():
    """When LLM_PROVIDER=bedrock, the dispatcher should delegate to the
    bedrock_chat module."""
    fake_parsed = _Greeting(text="bedrock hi", confidence=0.7)

    with patch.object(llm.settings, "llm_provider", "bedrock"), \
         patch.object(llm.bedrock_chat, "chat_structured", return_value=fake_parsed) as mock_bedrock:
        result = llm.chat_structured(
            messages=[{"role": "user", "content": "hi"}],
            response_model=_Greeting,
        )

    assert result == fake_parsed
    mock_bedrock.assert_called_once()


def test_chat_text_routes_to_bedrock_when_provider_is_bedrock():
    with patch.object(llm.settings, "llm_provider", "bedrock"), \
         patch.object(llm.bedrock_chat, "chat_text", return_value="from bedrock") as mock_bedrock:
        result = llm.chat_text(messages=[{"role": "user", "content": "hi"}])

    assert result == "from bedrock"
    mock_bedrock.assert_called_once()
