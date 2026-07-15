# ---------------------------------------------------------------------------
# Daily Comfort — Docker image
# ---------------------------------------------------------------------------
#
# Build:  docker build -t daily-comfort .
# Run:    docker run -d --env-file .env --env APP_PORT=8080 -p 8080:8080 daily-comfort
#
# Required environment variables (see .env.example):
#   LLM_ENDPOINT, LLM_MODEL, LLM_API_KEY, SERPAPI_API_KEY, APP_PORT
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Stage 1: Build — install dependencies into a clean site-packages
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: Production — slim runtime image
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS production

# Avoid .pyc files in images and buffers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy installed dependencies from builder stage
COPY --from=builder /install /usr/local

# Copy application source and static assets
COPY main.py config.py ./
COPY app/ ./app/
COPY static/ ./static/
COPY .env.example .

# Create a directory for generated animation HTML files at runtime
RUN mkdir -p /app/static/animations && \
    chown -R nobody:nogroup /app

# Drop privileges — run as non-root user
USER nobody

EXPOSE 8080

# Start the Uvicorn ASGI server (reloader disabled in production)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
