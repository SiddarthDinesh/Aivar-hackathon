from app.audit import AuditEvent, create_audit_event


def test_audit_schema_is_standardized_across_providers() -> None:
    event = create_audit_event(
        request_id="req-1",
        provider="mock",
        model="mock-model",
        action="generate",
        rule_result="allow",
        rule_name="default",
        rule_version="v1",
        request_identifier="req-1",
        response_identifier="resp-1",
    )

    assert isinstance(event, AuditEvent)
    assert event.request_id == "req-1"
    assert event.provider == "mock"
    assert event.action == "generate"
    assert event.rule_result == "allow"
    assert event.rule_name == "default"
    assert event.rule_version == "v1"
    assert event.request_identifier is not None
    assert event.request_identifier.startswith("sha256:")
    assert event.response_identifier is not None
    assert event.response_identifier.startswith("sha256:")
