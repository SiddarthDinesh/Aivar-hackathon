from __future__ import annotations

import os
from typing import Any

from app.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    """Adapter for the OpenAI Responses API."""

    def __init__(self, client: Any | None = None, model: str | None = None, api_key: str | None = None) -> None:
        self._client = client
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")

    def generate(self, prompt: str) -> str:
        if self._client is None and not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured")

        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover - defensive
                raise RuntimeError("The openai package is not installed") from exc

            self._client = OpenAI(api_key=self.api_key)

        response = self._client.responses.create(
            model=self.model,
            input=prompt,
        )

        choices = getattr(response, "choices", None)
        if choices:
            message = getattr(choices[0], "message", None)
            if message is not None:
                return getattr(message, "content", "")

        if hasattr(response, "output_text"):
            return str(response.output_text)

        raise RuntimeError("Unexpected OpenAI response format")
