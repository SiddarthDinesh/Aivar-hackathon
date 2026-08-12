import os
from unittest.mock import Mock, patch

from app.providers.openai_provider import OpenAIProvider


@patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False)
def test_openai_provider_returns_normalized_response() -> None:
    fake_client = Mock()
    fake_response = Mock()
    fake_response.choices = [Mock(message=Mock(content="hello from openai"))]
    fake_client.responses.create.return_value = fake_response

    provider = OpenAIProvider(client=fake_client, model="gpt-4.1-mini")

    result = provider.generate("Hello")

    assert result == "hello from openai"
    fake_client.responses.create.assert_called_once()


@patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False)
def test_openai_provider_uses_environment_api_key() -> None:
    fake_client = Mock()
    fake_response = Mock()
    fake_response.choices = [Mock(message=Mock(content="ok"))]
    fake_client.responses.create.return_value = fake_response

    provider = OpenAIProvider(client=fake_client, model="gpt-4.1-mini")

    assert provider.api_key == "test-key"
    assert provider.model == "gpt-4.1-mini"
