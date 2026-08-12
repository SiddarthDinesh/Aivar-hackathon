from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_end_to_end_flow_creates_audit_log(tmp_path: Path) -> None:
    log_path = tmp_path / "audit.jsonl"

    response = client.post(
        "/generate",
        json={"provider": "mock", "prompt": "Hello"},
    )

    assert response.status_code == 200
    assert response.json()["response"] == "mock-response:Hello"

    assert log_path.exists() is False
