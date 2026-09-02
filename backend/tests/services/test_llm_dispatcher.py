"""Provider dispatcher tests.

The dispatcher routes on settings.llm_provider:
  "github" (default) -> services.github_chat
  "bedrock"          -> services.bedrock_chat (legacy AWS path)

We verify chat_structured / chat_text delegate to the right provider
module with arguments unchanged.
"""

from __future__ import annotations

from unittest.mock import patch

from pydantic import BaseModel

from src.app.services import github_chat, llm
from src.settings import settings


class _Greeting(BaseModel):
    text: str
    confidence: float


def test_chat_structured_delegates_to_github_by_default():
    assert settings.llm_provider == "github"
    fake_parsed = _Greeting(text="hi", confidence=0.9)

    with patch.object(github_chat, "chat_structured", return_value=fake_parsed) as mock:
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


def test_chat_text_delegates_to_github_by_default():
    with patch.object(github_chat, "chat_text", return_value="gh hi") as mock:
        result = llm.chat_text(messages=[{"role": "user", "content": "hi"}])

    assert result == "gh hi"
    mock.assert_called_once()


def test_chat_structured_passes_through_model_override():
    fake_parsed = _Greeting(text="x", confidence=0.5)

    with patch.object(github_chat, "chat_structured", return_value=fake_parsed) as mock:
        llm.chat_structured(
            messages=[{"role": "user", "content": "?"}],
            response_model=_Greeting,
            model="custom-model-id",
            temperature=0.5,
        )

    kwargs = mock.call_args.kwargs
    assert kwargs["model"] == "custom-model-id"
    assert kwargs["temperature"] == 0.5


def test_bedrock_provider_flag_routes_to_bedrock():
    from src.app.services import bedrock_chat

    fake_parsed = _Greeting(text="br", confidence=1.0)
    with (
        patch.object(settings, "llm_provider", "bedrock"),
        patch.object(bedrock_chat, "chat_structured", return_value=fake_parsed) as mock,
    ):
        result = llm.chat_structured(
            messages=[{"role": "user", "content": "hi"}],
            response_model=_Greeting,
        )

    assert result == fake_parsed
    mock.assert_called_once()
