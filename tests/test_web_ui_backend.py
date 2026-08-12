from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_providers_endpoint_returns_supported_providers() -> None:
    response = client.get("/providers")

    assert response.status_code == 200
    assert response.json() == ["mock", "openai", "anthropic"]


def test_generate_response_includes_guardrail_and_audit_fields() -> None:
    response = client.post(
        "/generate",
        json={"provider": "mock", "prompt": "Hello"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["response"] == "mock-response:Hello"
    assert payload["guardrail_status"] == "allow"
    assert payload["rule"] == "placeholder-guardrail"
    assert payload["action"] == "allow"
    assert payload["request_id"]
    assert payload["timestamp"]
    assert payload["model"] is None or isinstance(payload["model"], str)
