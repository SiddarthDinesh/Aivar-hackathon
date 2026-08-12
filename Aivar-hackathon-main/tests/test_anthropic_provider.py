import os
from unittest.mock import Mock, patch

from app.providers.anthropic_provider import AnthropicProvider


@patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False)
def test_anthropic_provider_returns_normalized_response() -> None:
    fake_client = Mock()
    fake_response = Mock()
    fake_response.content = [Mock(text="hello from anthropic")]
    fake_client.messages.create.return_value = fake_response

    provider = AnthropicProvider(client=fake_client, model="claude-3-5-haiku-latest")

    result = provider.generate("Hello")

    assert result == "hello from anthropic"
    fake_client.messages.create.assert_called_once()


@patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False)
def test_anthropic_provider_uses_environment_api_key() -> None:
    fake_client = Mock()
    fake_response = Mock()
    fake_response.content = [Mock(text="ok")]
    fake_client.messages.create.return_value = fake_response

    provider = AnthropicProvider(client=fake_client, model="claude-3-5-haiku-latest")

    assert provider.api_key == "test-key"
    assert provider.model == "claude-3-5-haiku-latest"
