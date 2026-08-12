from app.audit import create_audit_event


def test_audit_event_uses_safe_identifiers() -> None:
    event = create_audit_event(
        request_id="req-1",
        provider="mock",
        model="mock-model",
        action="generate",
        rule_name="placeholder-guardrail",
        rule_version="v1",
        rule_result="allow",
        request_identifier="prompt:Hello",
        response_identifier="response:mock-response:Hello",
    )

    assert event.request_identifier is not None
    assert event.request_identifier.startswith("prompt:") is False
    assert event.request_identifier.startswith("sha256:")
    assert event.response_identifier is not None
    assert event.response_identifier.startswith("response:") is False
    assert event.response_identifier.startswith("sha256:")
