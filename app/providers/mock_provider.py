from app.providers.base import BaseProvider


class MockProvider(BaseProvider):
    """Simple deterministic provider for local testing and demos."""

    def generate(self, prompt: str) -> str:
        return f"mock-response:{prompt}"
