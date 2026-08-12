import hashlib
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from fastapi import HTTPException
from typing import Any
from pathlib import Path
import json
from datetime import datetime

from app.audit import create_audit_event
from app.audit_logger import AuditLogger
from app.guardrails import GuardrailEngine
from app.providers import get_provider

router = APIRouter()

audit_logger = AuditLogger(log_path="audit.jsonl")
guardrail_engine = GuardrailEngine()


class GenerateRequest(BaseModel):
    provider: Literal["mock", "openai", "anthropic"] = Field(..., description="Provider name: mock, openai, or anthropic")
    prompt: str = Field(..., min_length=1)


class GenerateResponse(BaseModel):
    provider: str
    prompt: str
    response: str
    guardrail_status: str
    rule: str | None = None
    action: str | None = None
    request_id: str | None = None
    timestamp: str | None = None
    model: str | None = None


@router.get("/")
async def root():
    # Serve the frontend index if it exists, otherwise return a simple health JSON.
    index_path = Path(__file__).resolve().parent.parent.parent / "app" / "static" / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"status": "ok", "message": "API running"}


@router.get("/providers")
async def providers() -> list[str]:
    return ["mock", "openai", "anthropic"]


@router.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest) -> GenerateResponse:
    provider = get_provider(request.provider)
    response_text = provider.generate(request.prompt)

    # Pass the provider output through the guardrail hook before recording it.
    guardrail_result = guardrail_engine.evaluate(response_text)

    safe_prompt_identifier = f"sha256:{hashlib.sha256(request.prompt.encode('utf-8')).hexdigest()}"
    safe_response_identifier = f"sha256:{hashlib.sha256(guardrail_result.output.encode('utf-8')).hexdigest()}"

    audit_event = create_audit_event(
        request_id=f"req-{abs(hash(request.prompt))}",
        provider=request.provider,
        model=getattr(provider, "model", None),
        action="generate",
        rule_name="placeholder-guardrail",
        rule_version="v1",
        rule_result=guardrail_result.status,
        request_identifier=safe_prompt_identifier,
        response_identifier=safe_response_identifier,
        metadata={"guardrail_reason": guardrail_result.reason},
    )
    audit_logger.log(audit_event)

    return GenerateResponse(
        provider=request.provider,
        prompt=request.prompt,
        response=guardrail_result.output,
        guardrail_status=guardrail_result.status,
        rule="placeholder-guardrail",
        action=guardrail_result.status,
        request_id=audit_event.request_id,
        timestamp=audit_event.timestamp,
        model=getattr(provider, "model", None),
    )


def _read_audit_lines(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        with p.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []
    return records


@router.get("/analytics/summary")
async def analytics_summary() -> dict[str, Any]:
    records = _read_audit_lines(audit_logger.log_path)
    total = len(records)
    allowed = 0
    redacted = 0
    blocked = 0
    by_rule: dict[str, int] = {"pii": 0, "toxicity": 0, "topic": 0}

    for rec in records:
        status = str(rec.get("rule_result") or "").lower()
        if status in ("allow", "allowed"):
            allowed += 1
        elif status in ("redact", "redacted", "warning"):
            redacted += 1
        elif status in ("block", "blocked"):
            blocked += 1

        # Infer the specific rule (pii, toxicity, topic) from available fields.
        # The audit schema stores a generic rule_name (placeholder-guardrail)
        # and the guardrail reason in metadata.guardrail_reason. Use that
        # metadata to classify violations without changing the audit schema.
        key = None
        rule_field = rec.get("rule_name") or rec.get("rule")
        if isinstance(rule_field, str) and rule_field.lower() in by_rule:
            key = rule_field.lower()
        else:
            # Inspect metadata.guardrail_reason for hints
            meta = rec.get("metadata") or {}
            reason = str(meta.get("guardrail_reason") or "").lower()
            if "pii" in reason or "email" in reason or "phone" in reason or "pii detected" in reason:
                key = "pii"
            elif "toxicity" in reason or "toxic" in reason or "toxicity threshold" in reason:
                key = "toxicity"
            elif "topic" in reason or "restricted topic" in reason or "restricted" in reason:
                key = "topic"

        if key and key in by_rule:
            by_rule[key] += 1

    return {
        "total": total,
        "allowed": allowed,
        "redacted": redacted,
        "blocked": blocked,
        "by_rule": by_rule,
    }


@router.get("/analytics/timeline")
async def analytics_timeline() -> list[dict[str, Any]]:
    records = _read_audit_lines(audit_logger.log_path)
    if not records:
        return []

    buckets: dict[str, dict[str, int]] = {}
    for rec in records:
        ts = rec.get("timestamp")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts)
            key = dt.strftime("%H:%M")
        except Exception:
            continue

        if key not in buckets:
            buckets[key] = {"time": key, "allowed": 0, "redacted": 0, "blocked": 0}

        status = str(rec.get("rule_result") or "").lower()
        if status in ("allow", "allowed"):
            buckets[key]["allowed"] += 1
        elif status in ("redact", "redacted", "warning"):
            buckets[key]["redacted"] += 1
        elif status in ("block", "blocked"):
            buckets[key]["blocked"] += 1

    # Sort by time key
    items = list(buckets.values())
    items.sort(key=lambda x: x["time"])
    return items


@router.get("/audit")
async def audit_events() -> list[dict[str, Any]]:
    records = _read_audit_lines(audit_logger.log_path)
    out: list[dict[str, Any]] = []
    for rec in records:
        out.append(
            {
                "timestamp": rec.get("timestamp"),
                "provider": rec.get("provider"),
                "model": rec.get("model"),
                "rule": rec.get("rule_name"),
                "action": rec.get("action"),
                "status": rec.get("rule_result"),
                "request_id": rec.get("request_id"),
                "rule_version": rec.get("rule_version"),
            }
        )
    return out
