from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_serves_the_ui_page() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Multi-Provider LLM Guardrail" in response.text
