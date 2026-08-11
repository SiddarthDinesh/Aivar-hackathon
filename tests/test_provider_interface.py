from app.providers.base import BaseProvider


class DummyProvider(BaseProvider):
    def generate(self, prompt: str) -> str:
        return f"echo:{prompt}"


def test_base_provider_interface_can_be_implemented() -> None:
    provider = DummyProvider()

    result = provider.generate("Hello")

    assert result == "echo:Hello"
