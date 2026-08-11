from app.guardrails import GuardrailEngine, GuardrailResult


def test_guardrail_engine_returns_processed_response() -> None:
    engine = GuardrailEngine()

    result = engine.evaluate("hello")

    assert isinstance(result, GuardrailResult)
    assert result.status == "allow"
    assert result.output == "hello"
