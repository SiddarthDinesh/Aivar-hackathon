"""Launcher to start the app with a correct module path.

Run this from the repository root (the folder containing the inner project folder).
Set `GEMINI_API_KEY` in the environment if you want the mock provider to use Gemini.

Example (PowerShell):
  $env:GEMINI_API_KEY = "<your-key>"
  python run_server.py

This script finds the first subdirectory that contains an `app/` package and
prepends it to `sys.path` so `import app` works regardless of working dir.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Find candidate inner project dir (contains 'app' subfolder)
inner = None
for child in ROOT.iterdir():
    if child.is_dir() and (child / "app").is_dir():
        inner = child
        break

if inner is None:
    # Fallback: assume current folder is the project root
    inner = ROOT

sys.path.insert(0, str(inner.resolve()))

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting uvicorn for app from {inner} on {host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
