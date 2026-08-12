from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class AuditEvent:
    """Standardized audit event for provider calls and guardrail outcomes."""

    request_id: str
    timestamp: str
    provider: str
    model: str | None = None
    action: str = "generate"
    rule_name: str | None = None
    rule_version: str | None = None
    rule_result: str | None = None
    request_identifier: str | None = None
    response_identifier: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_audit_event(
    *,
    request_id: str,
    provider: str,
    model: str | None = None,
    action: str = "generate",
    rule_name: str | None = None,
    rule_version: str | None = None,
    rule_result: str | None = None,
    request_identifier: str | None = None,
    response_identifier: str | None = None,
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    def _to_safe_identifier(value: str | None) -> str | None:
        if value is None:
            return None
        return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"

    return AuditEvent(
        request_id=request_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        provider=provider,
        model=model,
        action=action,
        rule_name=rule_name,
        rule_version=rule_version,
        rule_result=rule_result,
        request_identifier=_to_safe_identifier(request_identifier),
        response_identifier=_to_safe_identifier(response_identifier),
        error=error,
        metadata=metadata or {},
    )
