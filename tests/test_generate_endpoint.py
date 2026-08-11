from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_generate_endpoint_returns_provider_response() -> None:
    response = client.post(
        "/generate",
        json={"provider": "mock", "prompt": "Hello"},
    )

    assert response.status_code == 200
    assert response.json()["response"] == "mock-response:Hello"


def test_generate_endpoint_rejects_unknown_provider() -> None:
    response = client.post(
        "/generate",
        json={"provider": "unknown", "prompt": "Hello"},
    )

    assert response.status_code == 422
