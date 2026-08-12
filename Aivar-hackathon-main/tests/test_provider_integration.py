import json
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.api import routes
from app.audit_logger import AuditLogger
from app.guardrails import GuardrailResult
from app.main import app
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.mock_provider import MockProvider
from app.providers.openai_provider import OpenAIProvider


client = TestClient(app)


def _make_openai_provider() -> OpenAIProvider:
    fake_client = Mock()
    fake_response = Mock()
    fake_response.choices = [Mock(message=Mock(content="hello from openai"))]
    fake_client.responses.create.return_value = fake_response
    return OpenAIProvider(client=fake_client, model="gpt-4.1-mini")


def _make_anthropic_provider() -> AnthropicProvider:
    fake_client = Mock()
    fake_response = Mock()
    fake_response.content = [Mock(text="hello from anthropic")]
    fake_client.messages.create.return_value = fake_response
    return AnthropicProvider(client=fake_client, model="claude-3-5-haiku-latest")


def test_same_request_flow_across_providers(tmp_path: Path) -> None:
    log_path = tmp_path / "audit.jsonl"
    guardrail_inputs: list[str] = []

    class RecordingGuardrail:
        def evaluate(self, text: str) -> GuardrailResult:
            guardrail_inputs.append(text)
            return GuardrailResult(status="allow", output=text, reason="ok")

    providers = [
        ("mock", MockProvider()),
        ("openai", _make_openai_provider()),
        ("anthropic", _make_anthropic_provider()),
    ]

    with patch.object(routes, "audit_logger", AuditLogger(log_path=str(log_path))), patch.object(
        routes, "guardrail_engine", RecordingGuardrail()
    ):
        for provider_name, provider in providers:
            with patch.object(routes, "get_provider", return_value=provider):
                response = client.post(
                    "/generate",
                    json={"provider": provider_name, "prompt": "Hello"},
                )

            assert response.status_code == 200
            payload = response.json()
            assert payload["provider"] == provider_name
            assert payload["prompt"] == "Hello"
            assert isinstance(payload["response"], str)
            assert payload["response"] == guardrail_inputs[-1]

            audit_lines = log_path.read_text(encoding="utf-8").strip().splitlines()
            assert len(audit_lines) >= 1
            audit_payload = json.loads(audit_lines[-1])
            assert audit_payload["provider"] == provider_name
            assert audit_payload["action"] == "generate"
            assert audit_payload["rule_result"] == "allow"
            assert audit_payload["request_id"]
