from app.providers import get_provider
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.mock_provider import MockProvider
from app.providers.openai_provider import OpenAIProvider


def test_get_provider_returns_mock_provider() -> None:
    provider = get_provider("mock")

    assert isinstance(provider, MockProvider)


def test_get_provider_returns_openai_provider() -> None:
    provider = get_provider("openai")

    assert isinstance(provider, OpenAIProvider)


def test_get_provider_returns_anthropic_provider() -> None:
    provider = get_provider("anthropic")

    assert isinstance(provider, AnthropicProvider)


def test_get_provider_rejects_unknown_provider() -> None:
    try:
        get_provider("unknown")
    except ValueError as exc:
        assert "Unknown provider" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unknown provider")
