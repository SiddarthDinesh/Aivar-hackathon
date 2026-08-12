import json
from pathlib import Path
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app


def _write_audit_lines(path: Path, records: list[dict]):
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec))
            fh.write("\n")


def test_empty_audit_endpoints(tmp_path, monkeypatch):
    audit_file = tmp_path / "audit.jsonl"
    # Ensure file does not exist
    if audit_file.exists():
        audit_file.unlink()

    # Point the app's audit logger path to our temp file
    from app.api import routes

    routes.audit_logger.log_path = audit_file

    client = TestClient(app)

    r = client.get("/analytics/summary")
    assert r.status_code == 200
    assert r.json() == {
        "total": 0,
        "allowed": 0,
        "redacted": 0,
        "blocked": 0,
        "by_rule": {"pii": 0, "toxicity": 0, "topic": 0},
    }

    r = client.get("/analytics/timeline")
    assert r.status_code == 200
    assert r.json() == []

    r = client.get("/audit")
    assert r.status_code == 200
    assert r.json() == []


def test_audit_endpoints_with_records(tmp_path):
    audit_file = tmp_path / "audit.jsonl"

    now = datetime.now(timezone.utc).isoformat()
    records = [
        {
            "request_id": "r1",
            "timestamp": now,
            "provider": "mock",
            "model": "m1",
            "action": "generate",
            "rule_name": "placeholder-guardrail",
            "rule_version": "v1",
            "rule_result": "redact",
            "metadata": {"guardrail_reason": "PII detected"},
        },
        {
            "request_id": "r2",
            "timestamp": now,
            "provider": "mock",
            "model": "m1",
            "action": "generate",
            "rule_name": "placeholder-guardrail",
            "rule_version": "v1",
            "rule_result": "block",
            "metadata": {"guardrail_reason": "Toxicity threshold exceeded"},
        },
        {
            "request_id": "r3",
            "timestamp": now,
            "provider": "mock",
            "model": "m1",
            "action": "generate",
            "rule_name": "placeholder-guardrail",
            "rule_version": "v1",
            "rule_result": "allow",
            "metadata": {"guardrail_reason": "No policy violations detected"},
        },
    ]

    _write_audit_lines(audit_file, records)

    from app.api import routes

    routes.audit_logger.log_path = audit_file

    client = TestClient(app)

    r = client.get("/analytics/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert body["allowed"] == 1
    assert body["redacted"] == 1
    assert body["blocked"] == 1
    assert body["by_rule"]["pii"] == 1
    assert body["by_rule"]["toxicity"] == 1
    assert body["by_rule"]["topic"] == 0

    r = client.get("/analytics/timeline")
    assert r.status_code == 200
    timeline = r.json()
    # Should have at least one bucket
    assert isinstance(timeline, list)
    assert len(timeline) >= 1
    # Check sums match
    s_allowed = sum(item.get("allowed", 0) for item in timeline)
    s_redacted = sum(item.get("redacted", 0) for item in timeline)
    s_blocked = sum(item.get("blocked", 0) for item in timeline)
    assert s_allowed == 1
    assert s_redacted == 1
    assert s_blocked == 1

    r = client.get("/audit")
    assert r.status_code == 200
    audit = r.json()
    assert isinstance(audit, list)
    assert len(audit) == 3
    first = audit[0]
    assert first["provider"] == "mock"
    assert "timestamp" in first