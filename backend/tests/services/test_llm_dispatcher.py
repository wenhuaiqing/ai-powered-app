"""Provider dispatcher tests.

After Phase 2 step 6 the dispatcher is Bedrock-only -- we just verify
chat_structured / chat_text delegate to services.bedrock_chat with the
arguments unchanged.
"""

from __future__ import annotations

from unittest.mock import patch

from pydantic import BaseModel

from src.app.services import llm


class _Greeting(BaseModel):
    text: str
    confidence: float


def test_chat_structured_delegates_to_bedrock():
    fake_parsed = _Greeting(text="hi", confidence=0.9)

    with patch.object(llm.bedrock_chat, "chat_structured", return_value=fake_parsed) as mock:
        result = llm.chat_structured(
            messages=[{"role": "user", "content": "hi"}],
            response_model=_Greeting,
        )

    assert result == fake_parsed
    mock.assert_called_once()
    # messages + response_model passed positionally, model + temperature as kwargs.
    args, kwargs = mock.call_args
    assert args[1] is _Greeting
    assert kwargs["temperature"] == 0.0
    assert kwargs["model"] is None


def test_chat_text_delegates_to_bedrock():
    with patch.object(llm.bedrock_chat, "chat_text", return_value="bedrock hi") as mock:
        result = llm.chat_text(messages=[{"role": "user", "content": "hi"}])

    assert result == "bedrock hi"
    mock.assert_called_once()


def test_chat_structured_passes_through_model_override():
    fake_parsed = _Greeting(text="x", confidence=0.5)

    with patch.object(llm.bedrock_chat, "chat_structured", return_value=fake_parsed) as mock:
        llm.chat_structured(
            messages=[{"role": "user", "content": "?"}],
            response_model=_Greeting,
            model="custom-model-id",
            temperature=0.5,
        )

    kwargs = mock.call_args.kwargs
    assert kwargs["model"] == "custom-model-id"
    assert kwargs["temperature"] == 0.5
