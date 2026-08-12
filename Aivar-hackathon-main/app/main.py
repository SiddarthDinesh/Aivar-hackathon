from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

app = FastAPI(title="Multi-Provider LLM Guardrail")
app.include_router(router)

# Mount static files using an absolute path so the server can be started
# from any working directory (avoids RuntimeError when 'app/static' isn't found).
STATIC_DIR = BASE_DIR / "app" / "static"
if STATIC_DIR.exists():
	app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Lambda handler for AWS deployment
try:
	from mangum import Mangum
	handler = Mangum(app, lifespan="off")
except ImportError:
	# Fallback if mangum is not installed (for local development)
	handler = None
