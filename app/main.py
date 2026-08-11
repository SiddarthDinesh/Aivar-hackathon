from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

app = FastAPI(title="Multi-Provider LLM Guardrail")
app.include_router(router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
