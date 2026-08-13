Multi-Provider LLM Guardrail

This prototype provides a small FastAPI app that can route requests to a mock, OpenAI, or Anthropic provider, pass the result through a placeholder guardrail integration point, and write a standardized audit event to a JSONL file.

Setup

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

Environment Variables

Copy ".env.example" to ".env":

copy .env.example .env

API Keys

The mock provider does not require an API key and can be used to test the application locally.

The OpenAI and Anthropic providers require their respective API keys. These keys are not included with this project and must be obtained and configured by the user.

For OpenAI:

OPENAI_API_KEY=your_openai_api_key_here

For Anthropic:

ANTHROPIC_API_KEY=your_anthropic_api_key_here

If you do not have OpenAI or Anthropic API access/credits, you can still run the complete application using the "mock" provider.

Important: Never commit your ".env" file or expose your API keys publicly. The ".env.example" file contains only placeholder values.

Run

Start the FastAPI application with:

uvicorn app.main:app --reload

The application will be available at:

http://127.0.0.1:8000

Test

Run the automated tests with:

pytest -q

Example Request — Mock Provider

The mock provider can be used without any API key:

curl -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"provider": "mock", "prompt": "Hello"}'

Using OpenAI or Anthropic

Once the appropriate API key has been added to ".env", the corresponding provider can be selected in the request.

For example:

{
  "provider": "openai",
  "prompt": "Hello"
}

or:

{
  "provider": "anthropic",
  "prompt": "Hello"
}

The application then routes the request to the selected provider, passes the generated response through the guardrail integration point, and records a standardized audit event in the JSONL audit log.