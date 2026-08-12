import json
from pathlib import Path

from app.audit import AuditEvent, create_audit_event
from app.audit_logger import AuditLogger


def test_audit_logger_writes_json_lines(tmp_path: Path) -> None:
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path=str(log_path))

    event = create_audit_event(
        request_id="req-1",
        provider="mock",
        model="mock-model",
        action="generate",
        rule_result="allow",
    )

    logger.log(event)

    saved_lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(saved_lines) == 1

    payload = json.loads(saved_lines[0])
    assert payload["request_id"] == "req-1"
    assert payload["provider"] == "mock"
    assert payload["action"] == "generate"
    assert payload["rule_result"] == "allow"
