from __future__ import annotations

import os
from typing import Any

from app.providers.base import BaseProvider


class AnthropicProvider(BaseProvider):
    """Adapter for the Anthropic Messages API."""

    def __init__(self, client: Any | None = None, model: str | None = None, api_key: str | None = None) -> None:
        self._client = client
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")

    def generate(self, prompt: str) -> str:
        if self._client is None and not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not configured")

        if self._client is None:
            try:
                from anthropic import Anthropic
            except ImportError as exc:  # pragma: no cover - defensive
                raise RuntimeError("The anthropic package is not installed") from exc

            self._client = Anthropic(api_key=self.api_key)

        response = self._client.messages.create(
            model=self.model,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )

        content = getattr(response, "content", None)
        if content:
            first_block = content[0]
            text = getattr(first_block, "text", None)
            if text is not None:
                return str(text)

        raise RuntimeError("Unexpected Anthropic response format")
