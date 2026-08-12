# Multi-Provider LLM Guardrail

This prototype provides a small FastAPI app that can route requests to a mock, OpenAI, or Anthropic provider, pass the result through a placeholder guardrail integration point, and write a standardized audit event to a JSONL file.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Environment variables

Copy [.env.example](.env.example) to .env and set any provider API keys you plan to use:

```bash
copy .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload
```

## Test

```bash
pytest -q
```

## Example request

```bash
curl -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"provider": "mock", "prompt": "Hello"}'
```
