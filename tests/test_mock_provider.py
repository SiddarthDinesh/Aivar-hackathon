from app.providers.mock_provider import MockProvider


def test_mock_provider_returns_deterministic_response() -> None:
    provider = MockProvider()

    response = provider.generate("Hello")

    assert response == "mock-response:Hello"
