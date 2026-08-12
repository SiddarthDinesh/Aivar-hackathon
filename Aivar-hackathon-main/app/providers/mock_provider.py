from __future__ import annotations

import json
import os
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from app.providers.base import BaseProvider


class MockProvider(BaseProvider):
    """Simple deterministic provider for local testing and demos.

    If `GEMINI_API_KEY` is configured, this provider will attempt to call
    Google's Generative Language API (Gemini) for a real response. On any
    failure it falls back to the deterministic mock response, preserving
    existing test and demo behavior.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None, client: Any | None = None) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        # default to a commonly available text model; can be overridden
        self.model = model or os.getenv("GEMINI_MODEL", "text-bison-001")
        self._client = client

    def generate(self, prompt: str) -> str:
        # If no Gemini key configured, use deterministic mock behavior
        if not self.api_key:
            return f"mock-response:{prompt}"

        # Attempt a minimal POST to the Generative Models generate endpoint
        url = f"https://generativelanguage.googleapis.com/v1beta2/models/{self.model}:generate?key={self.api_key}"
        body = {"prompt": {"text": prompt}}
        data = json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json; charset=utf-8"}

        req = Request(url, data=data, headers=headers, method="POST")
        try:
            with urlopen(req, timeout=15) as resp:
                resp_data = resp.read().decode("utf-8")
                parsed = json.loads(resp_data or "{}")
                # response shape: {"candidates": [{"content": "..."}, ...]}
                candidates = parsed.get("candidates") or parsed.get("candidates", [])
                if isinstance(candidates, list) and candidates:
                    first = candidates[0]
                    content = first.get("content")
                    if content:
                        return str(content)
                # Some API versions use 'outputs' or 'reply' fields — try common alternatives
                if "output" in parsed and isinstance(parsed["output"], str):
                    return parsed["output"]
                if "outputs" in parsed and isinstance(parsed["outputs"], list) and parsed["outputs"]:
                    out0 = parsed["outputs"][0]
                    if isinstance(out0, dict) and "content" in out0:
                        return str(out0["content"])

        except HTTPError as he:
            # Do not raise — fall back to mock response
            pass
        except URLError as ue:
            pass
        except Exception:
            pass

        # Fallback deterministic response
        return f"mock-response:{prompt}"
