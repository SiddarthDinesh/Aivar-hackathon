from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.audit import AuditEvent


class AuditLogger:
    """Simple JSON Lines audit logger for the prototype."""

    def __init__(self, log_path: str | None = None) -> None:
        self.log_path = Path(log_path or "audit.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: AuditEvent) -> dict[str, Any]:
        payload = event.to_dict()
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True))
            handle.write("\n")
        return payload
