"""Tests for the FastAPI main application endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport
from sse_starlette.sse import EventSourceResponse

from main import app


class TestRootEndpoint:
    """Tests for GET / (HTML page)."""

    @pytest.mark.asyncio
    async def test_root_returns_html(self):
        """Root endpoint should return an HTML page with the SSE client script."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
            assert "Daily Comfort" in response.text
            assert "/static/app.js" in response.text


class TestHealthEndpoint:
    """Tests for GET /health."""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self):
        """Health endpoint should return a JSON ok status."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}


class TestStreamEndpoint:
    """Tests for GET /api/stream (SSE)."""

    @pytest.mark.asyncio
    async def test_stream_returns_sse(self):
        """Stream endpoint should return SSE-compatible response."""
        from unittest.mock import AsyncMock

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            with patch("main.stream_comfort", new_callable=AsyncMock) as mock_stream:
                mock_stream.return_value = EventSourceResponse(
                    content=mock_async_generator(),
                )
                response = await client.get("/api/stream")
                assert response.status_code == 200
                # SSE response has content-type text/event-stream
                assert "event-stream" in response.headers["content-type"]


async def mock_async_generator():
    """Generate a fake SSE event for testing."""
    yield {"event": "done", "data": '{"hot_news":"","feeling":"","comfort":""}'}
