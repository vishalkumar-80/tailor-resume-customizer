# Entrypoint for Vercel's Python runtime (it looks for an `app` object here).
from app.main import app

__all__ = ["app"]
