from __future__ import annotations

from typing import TYPE_CHECKING

from app.guardrail_policy import Policy, evaluate_text

if TYPE_CHECKING:
    from app.guardrails import GuardrailResult


class GuardrailAdapter:
    """Adapter from the teammate policy engine to the app's GuardrailResult interface."""

    def __init__(self, policy: Policy | None = None) -> None:
        self.policy = policy or Policy.from_rules(
            [
                {
                    "id": "pii",
                    "type": "pii",
                    "scope": "output",
                    "action": "redact",
                },
                {
                    "id": "toxicity",
                    "type": "toxicity",
                    "scope": "output",
                    "action": "block",
                    "threshold": 0.8,
                },
                {
                    "id": "restricted_topics",
                    "type": "topic",
                    "scope": "input",
                    "action": "block",
                    "keywords": ["malware", "terrorism", "weapons"],
                },
            ]
        )

    def evaluate(self, text: str):
        from app.guardrails import GuardrailResult

        result = evaluate_text(text, self.policy, scope="output")
        action = str(result.get("action", "allow"))
        if action == "redact":
            return GuardrailResult(status="redact", output=str(result.get("redacted_text", text)), reason=str(result.get("reason", "redacted")))
        if action == "block":
            return GuardrailResult(status="block", output=text, reason=str(result.get("reason", "blocked")))
        return GuardrailResult(status="allow", output=text, reason=str(result.get("reason", "allowed")))
