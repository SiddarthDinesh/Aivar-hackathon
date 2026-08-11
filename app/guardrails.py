from __future__ import annotations

from dataclasses import dataclass

from app.guardrail_adapter import GuardrailAdapter


@dataclass(frozen=True)
class GuardrailResult:
    """Simple contract for a guardrail evaluation result."""

    status: str
    output: str
    reason: str | None = None


class GuardrailEngine:
    """Adapter around the teammate policy engine while preserving the app interface."""

    def __init__(self) -> None:
        self._adapter = GuardrailAdapter()

    def evaluate(self, text: str) -> GuardrailResult:
        """Evaluate the provided text using the teammate policy engine."""
        return self._adapter.evaluate(text)
