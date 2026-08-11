import hashlib
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

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
async def root() -> FileResponse:
    return FileResponse("app/static/index.html")


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
