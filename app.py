"""Vercel FastAPI entrypoint.

Vercel auto-detects FastAPI apps from files such as app.py, index.py, or
server.py. The actual application lives in backend.py for local development.
"""

from backend import app

