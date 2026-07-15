"""
FastAPI entry point for Daily Comfort.

The root endpoint (GET /) serves the static HTML frontend and starts
the LangGraph workflow via the SSE stream endpoint (/api/stream).
"""

import logging
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from app.streaming import stream_comfort
from config import APP_PORT

# Configure root logger to DEBUG level for verbose output
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# Add a console handler with proper formatting if none exists
if not root_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setLevel(logging.DEBUG)
    _formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    _handler.setFormatter(_formatter)
    root_logger.addHandler(_handler)

logger = logging.getLogger(__name__)

# Suppress asyncio internal DEBUG logs (e.g. "Using selector: EpollSelector")
logging.getLogger("asyncio").setLevel(logging.WARNING)

# Suppress sse_starlette heartbeat ping DEBUG logs (": ping")
logging.getLogger("sse_starlette.sse").setLevel(logging.WARNING)

app = FastAPI(
    title="Daily Comfort",
    description="A LangGraph workflow that fetches HK news, generates feelings, and offers pastoral comfort via SSE.",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Static file serving
# ---------------------------------------------------------------------------

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---------------------------------------------------------------------------
# Root endpoint — serves the HTML frontend
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the static index.html page."""
    logger.debug("GET / — serving static index.html")
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# ---------------------------------------------------------------------------
# SSE stream endpoint (delegates to app.streaming)
# ---------------------------------------------------------------------------

@app.get("/api/stream")
async def api_stream():
    """
    Stream the LangGraph workflow results as Server-Sent Events.

    Events:
      - news      : Formatted hot news
      - feeling   : LLM-generated feeling/emotion
      - comfort   : LLM-generated pastoral comfort
      - done      : Final complete payload (JSON)
      - error     : Error event with details
    """
    logger.debug("GET /api/stream — SSE stream request received, starting LangGraph workflow")
    return await stream_comfort()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Simple health check endpoint."""
    logger.debug("GET /health — health check")
    return {"status": "ok"}
