# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- **Comprehensive debug logging across all modules**
  - `main.py` — Root logger set to `DEBUG` level with a console handler; debug log on every API request (`GET /`, `GET /api/stream`, `GET /health`)
  - `app/streaming.py` — Debug log on SSE stream init, each event type received (with node name), token chunk sizes, node completion char counts, final `done` event, and exception details
  - `app/workflow.py` — Debug log on graph build (nodes added, edges defined, entry/exit points set, compilation)
  - `app/nodes/fetch_news.py` — Debug log on SerpApi client creation, search params, response keys, and article count
  - `app/nodes/generate_feeling.py` — Debug log on LLM config (endpoint, model, key length), prepared messages, system prompt, user prompt preview, model invocation, and response preview
  - `app/nodes/generate_comfort.py` — Debug log on LLM config, prepared messages, system prompt, user prompt preview, model invocation, and response preview
  - All HTTP client debug logs (urllib3, httpcore, openai, httpx) are now visible at debug level

### Fixed

- `tests/test_main.py` — Fixed `test_root_returns_html`: assertion now checks for `"/static/app.js"` in HTML instead of the non-existent `"EventSource"` string
- `tests/test_main.py` — Fixed `test_stream_returns_sse`: mocks `stream_comfort` with `AsyncMock` and a fake async generator instead of triggering the real workflow (which hung due to missing LLM server)

### Changed

- `main.py` — Added root logger configuration with formatted console handler (timestamp + level + name + message)
- `requirements.txt` — No changes needed
