import os

from app.providers.anthropic_provider import AnthropicProvider
from app.providers.base import BaseProvider
from app.providers.mock_provider import MockProvider
from app.providers.openai_provider import OpenAIProvider


def get_provider(name: str) -> BaseProvider:
    """Return a provider instance for the requested name."""
    provider_name = (name or "").strip().lower()

    if provider_name == "mock":
        return MockProvider()
    if provider_name == "openai":
        return OpenAIProvider()
    if provider_name == "anthropic":
        return AnthropicProvider()
    if provider_name == "gemini":
        # Return the mock adapter configured to call Gemini when GEMINI_API_KEY is set.
        return MockProvider(api_key=os.getenv("GEMINI_API_KEY"))

    raise ValueError(f"Unknown provider: {name}")
