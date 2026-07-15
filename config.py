"""
Configuration loader for Daily Comfort.

Reads environment variables from .env (via python-dotenv) and exposes
typed defaults so the app runs locally without manual setup.
"""

import os
from dotenv import load_dotenv

# Load .env file if present (no error if missing)
load_dotenv()


def get_env(key: str, default: str) -> str:
    """Retrieve an environment variable with a fallback default."""
    return os.getenv(key, default)


# -- LLM Configuration --
# OpenAI-compatible API base URL
LLM_ENDPOINT: str = get_env("LLM_ENDPOINT", "http://localhost:8000/v1")

# Model identifier
LLM_MODEL: str = get_env("LLM_MODEL", "Ornith-1.0-35B")

# Port used by the upstream LLM server (informational only)
LLM_PORT: int = int(get_env("LLM_PORT", "8000"))

# API key for the upstream LLM server
LLM_API_KEY: str = get_env("LLM_API_KEY", "nokey")

# -- SerpApi --
# API key for SerpApi (Google Search with tbm=nws for news)
SERPAPI_API_KEY: str = get_env("SERPAPI_API_KEY", "")

# -- FastAPI Server --
# Port the FastAPI server binds to
APP_PORT: int = int(get_env("APP_PORT", "8080"))
