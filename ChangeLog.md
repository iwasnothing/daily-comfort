# Changelog

All notable changes to Daily Comfort are documented in this file.

## [Unreleased]

### Changed
- **Animation URL rendered as clickable `<a>` link in table row**: `static/app.js` — the animation event handler now wraps the URL in `<a href="..." target="_blank" class="animation-link">` instead of plain text, so users can click to open the animation page directly.

### Changed
- **Animation renders as inline iframe instead of clickable link**: `static/app.js` and `static/index.html` — when the animation event arrives, the animation is now rendered as an `<iframe>` below the result table (with header "🎨 動畫預覽"), instead of showing the URL as a plain text link in the table row. The table row still displays the animation URL path. The iframe uses `sandbox="allow-scripts allow-same-origin"` for security. The animation container is cleared when the user clicks "重新生成" to start a new run.

### Changed
- **Animation row shows clickable HTTP link instead of "iframe" placeholder**: `static/app.js` — the animation event handler now renders the animation URL as a clickable `<a>` link (`<a href="${data.url}" target="_blank" rel="noopener noreferrer">${data.url}</a>`) in the table row, replacing the previous `<em>` message "動畫已生成，請參閱上方 iframe".
- **Removed orphaned animation iframe container**: Removed the `<div id="animation-container">` block and `.animation-cell iframe` CSS rule from `static/index.html` — no longer needed since the animation is accessed via clickable link instead of inline iframe embed.

### Changed
- **News list now uses HTML `<ul>` bullet list**: `app/nodes/fetch_news.py` now wraps each news item in `<li>` tags inside a `<ul class="news-list">` instead of numbered `1.`, `2.` format. Source name and date appear in a `<span class="news-meta">` with a `·` bullet separator.
- **Dates displayed in human-friendly Chinese format**: `app/nodes/fetch_news.py` added `_format_date_human_friendly()` helper that converts SerpApi datetime strings (e.g., `"Wed, 15 Jul 2026 10:01:40 GMT"`, `"07/13/2026, 08:08 AM, +0000 UTC"`) to Chinese format (e.g., `"2026年7月15日 星期三"`). Handles timezone name suffixes (UTC, HKT, CST, etc.) and numeric offsets (`+0000`, `+0800`, etc.).
- **News titles are now clickable hyperlinks**: `app/nodes/fetch_news.py` no longer prints the article URL on a separate `Link:` line. Instead, each title is wrapped in an `<a href="...">` tag so users can click through to the source article. Added `target="_blank"` and `rel="noopener noreferrer"` for security. The news field now returns HTML instead of plain text.
- **Skip malformed news articles**: `app/nodes/fetch_news.py` now skips individual articles that have missing, empty, or `"Untitled"` titles (indicating a malformed SerpApi response). If all articles are skipped, the node returns `"(All news articles have missing or invalid titles.)"` instead of an empty string.
- **Frontend renders HTML for the news row**: `static/app.js` — `upsertRow()` now accepts an `isHtml` flag. The news event handler passes `isHtml = true` so the news cell uses `innerHTML` (rendering clickable links) while all other cells still use escaped text. See `static/app.js`.
- **Unit tests updated**: `tests/test_workflow.py::test_fetches_and_formats_news` now asserts that titles are wrapped in `<a href=...>` tags and that `"Link:"` no longer appears in the output. Added `test_skips_unfinished_articles` and `test_returns_message_when_all_articles_skipped`.

### Fixed
- **SerpApi 400 Bad Request on news fetch**: The `hl=zh-Hant` parameter is not a valid SerpApi interface language — SerpApi returns `"Unsupported zh-Hant interface language - hl parameter."`. Additionally, the `google_news` engine does not support complex Google search operators (`()`, `OR`, `site:`, `""`, `-`) that the regular `google` engine supports. Fixed by removing the `hl` parameter and simplifying the query to plain text `"香港"` with `gl=hk` and `tbs=qdr:d` for today's Hong Kong news in Traditional Chinese. Updated `tests/test_workflow.py::test_uses_correct_serpapi_parameters` to match.

### Changed
- **`app/nodes/fetch_news.py`**: Removed invalid `hl: zh-Hant` parameter and replaced the complex boolean query string (using `site:`, `OR`, `-` operators) with a simple Chinese query `"香港"`. The `gl=hk` parameter handles location targeting, and Chinese query terms naturally return Traditional Chinese titles from the `google_news` engine.

### Removed
- **Streaming token debug log in `generate_feeling`**: Removed `logger.debug("Node [generate_feeling] — token chunk: %s", content[:50])` from the `astream()` loop in `app/nodes/generate_feeling.py` — it produced excessive DEBUG output per streamed token without useful context.

### Changed
- **Graceful handling of missing/undefined SSE data**: Added `extractContent(data)` helper in `static/app.js` that safely returns a string from SSE event payloads — handles missing `content` property, non-string data, and empty strings (falls back to "(無內容)"). The `steps` array now includes the `animation` entry so `upsertRow(3)` no longer throws when accessing `steps[3].label`.

### Fixed
- **Animation iframe too short**: Increased the `.animation-cell iframe` CSS `min-height` from `400px` to `500px` and `max-height` from `70vh` to `90vh` so the animation can display fully without being clipped. See `static/index.html`.
- **Animation HTML not served by static file mount**: The `generate_animation` node returned the animation URL as `/animation_{timestamp}.html`, but FastAPI mounts static files at `/static`. The iframe `src` could never resolve. Fixed `_save_html` in `app/nodes/generate_animation.py` to return `/static/{filename}`. See `app/nodes/generate_animation.py`.
- **Removed streaming token debug log**: Removed the verbose `logger.debug("Streaming: token chunk...")` line from `app/streaming.py`'s `on_chat_model_stream` handler to reduce excessive DEBUG output per token.
- **SSE no longer streams HTML content from `generate_animation`**: Added a guard in `app/streaming.py` that skips `on_chat_model_stream` token events when `current_workflow_node == "generate_animation"`. The node uses `ainvoke()` to save HTML to `static/animation_{timestamp}.html` and returns only the URL via `on_chain_end`. Previously, LangGraph's event system emitted token-by-token `on_chat_model_stream` events for the animation node, flooding the SSE feed with large HTML markup payloads. Now only the final `animation` event with the URL is sent. See `app/streaming.py`, `tests/test_streaming.py::test_animation_node_skips_streaming_tokens`.

### Added
- **Node 4 — `generate_animation`**: New LangGraph node that calls the LLM to generate a self-contained HTML/CSS animation illustrating the pastoral comfort message. The generated HTML is saved to `static/animation_{timestamp}.html` and the URL is returned in the state. Uses `ANIMATION_TEMPERATURE` env variable (default 0.8) for creative temperature. Strips markdown code fences from LLM output. See `app/nodes/generate_animation.py`.
- **`ComfortState.animation` field**: Added `animation: str` field to the Pydantic state model for storing the animation URL path.
- **SSE `animation` event**: The streaming layer now emits an `animation` SSE event containing the animation file URL when Node 4 completes.
- **Frontend animation container**: Added a dedicated `<div>` below the result table that renders the animation as an `<iframe>` when the animation event arrives. See `static/index.html`, `static/app.js`.
- **`ANIMATION_TEMPERATURE` env variable**: LLM temperature for animation generation (creative), default `0.8`. See `config.py`.

### Changed
- **`generate_animation` node no longer streams HTML content**: Switched from `model.astream()` to `model.ainvoke()`. The generated HTML is saved to `static/animation_{timestamp}.html` and only the URL path is streamed back via SSE. This eliminates noisy token-level debug logs and avoids flooding the SSE stream with large HTML payloads. See `app/nodes/generate_animation.py`.
- **Removed streaming token debug log from SSE**: Removed `logger.debug("Streaming: [sse %s] token chunk: %.50s...")` from the `on_chat_model_stream` handler in `app/streaming.py` — token chunks are still forwarded to the client but no longer produce a DEBUG log per token.
- **LangGraph topology**: Extended to 4 nodes — `fetch_hot_news → generate_feeling → generate_comfort → generate_animation → end`.
- **Workflow graph compilation**: `build_graph()` in `app/workflow.py` now includes `generate_animation` node and edge.
- **SSE streaming**: `event_generator()` in `app/streaming.py` handles `animation` events from Node 4, and the `done` event now includes the `animation` field.
- **`NODE_TO_EVENT` mapping**: Added `"generate_animation": "animation"` mapping.
- **Frontend table**: Added an `animation` step to the result table (index 3) that shows a loading message until the iframe is rendered.
- **AGENTS.md**: Updated architecture diagram, workflow topology, node descriptions, SSE event table, and configuration table to reflect the new node.

### Fixed
- **Frontend SSE events never dispatched to handlers**: Replaced `es.onmessage` with `es.addEventListener(type, handler)` for each SSE event type (`news`, `feeling`, `comfort`, `done`, `error`, `close`, `open`). The `MessageEvent` object does NOT have an `event` property — `event.event` is always `undefined`, so `es.onmessage` with `event.event` never matches custom event types. This was the root cause of silent failure: no console output, no UI updates, no spinner clearing. Now uses `addEventListener` which is the correct API for custom SSE event types. Also added `console.log` debug output in every handler (`[SSE] Received event: ...`). See `static/app.js`.
- **SSE `onerror` false-positive console log**: The `onerror` handler in `static/app.js` called `console.error("SSE error:", err)` **before** the `readyState === CLOSED` guard. When the backend closes the connection normally (after `done` or `error` event), the browser fires `onerror` with `readyState: 2 (CLOSED)`, triggering the misleading error log. Moved `console.error` inside the `try` block, after the `CLOSED` check, so normal connection close no longer prints an error.
- **Frontend SSE event parsing**: The `onmessage` handler in `static/app.js` was reading `data.event` to check the event type, but the SSE `event` field is separate from the JSON `data` payload. The browser's `EventSource` exposes it as `event.event`, not inside the parsed JSON. Changed all event checks to use `event.event` instead of `data.event`, and content access to `data.content` instead of `data.data.content`. This was the root cause of the `readyState: 2 (CLOSED)` error — no event branches were ever matching, so the status spinner never cleared and the rows were never populated.
- **SSE `onerror` crash on frontend**: The `generate_feeling` and `generate_comfort` nodes used `model.invoke(messages)` which is a blocking synchronous call (~72 s for a 35 B model). During this wait no LLM token events were emitted, so the browser's `EventSource` eventually fired `onerror`. Switched both nodes to `async def` with `model.astream()` so `on_chat_model_stream` events are emitted in real time and forwarded through the SSE stream. See `app/nodes/generate_feeling.py`, `app/nodes/generate_comfort.py`.
- **SSE chunk events now include accumulated text**: The `on_chat_model_stream` handler in `app/streaming.py` now sends `data: {"chunk": "<token>", "content": "<accumulated text>"}` so the frontend can display the growing response progressively instead of seeing only single tokens.
- **`event_generator` extracted to module level**: The inner async generator `event_generator()` in `app/streaming.py` is now a top-level async function accepting `(graph)` so it can be unit-tested independently. `stream_comfort()` simply calls `event_generator(graph)` and wraps the result in `EventSourceResponse`.

### Added
- **SSE debug logging on frontend**: Added `console.log("[SSE] Received event:", eventType, "| data:", data)` in `static/app.js` `onmessage` handler for debugging incoming SSE events.
- **Unit tests for SSE format**: `tests/test_sse_format.py` covers the SSE event wire format, streaming chunk format, done event format, error event format, frontend event parsing logic, and documents the old buggy logic (6 tests total).
- **Unit tests for SSE streaming**: `tests/test_streaming.py` covers chunk format, accumulated text, final content, news events, error handling, empty graph, and the `NODE_TO_EVENT` mapping (9 tests total).

### Changed
- **`generate_feeling` / `generate_comfort` nodes are now async**: Function signature changed from `def node(state) -> dict` to `async def node(state) -> dict`. The async `astream()` loop collects chunks and joins them into the final text, which is returned in the state dict as before.

### Changed
- **Lazy workflow graph compilation**: The LangGraph workflow graph is now built at request time (when `/api/stream` is called) instead of at import time (server startup). `comfort_graph` module-level variable removed from `app/workflow.py`; `build_graph()` is now called inside `stream_comfort()` in `app/streaming.py`.

### Removed
- **Verbose streaming chunk debug log**: Removed the `logger.debug("Streaming: [%s] token chunk (%d chars)")` line from every LLM token chunk in `app/streaming.py` — it produced excessive DEBUG output for every streamed token.
- **sse_starlette ping debug logs**: Suppress `sse_starlette.sse` logger at WARNING level in `main.py` — the periodic ": ping" heartbeat messages were flooding DEBUG output without useful context.
- **Debug log in streaming**: Removed the verbose `logger.debug("Streaming: received event_type=..., node=...")` from every event in the `astream_events` loop in `app/streaming.py` — it emitted a DEBUG log for every internal event (e.g. `on_chat_model_stream` from `ChatOpenAI`), adding noise without useful context.

### Fixed
- **asyncio DEBUG log noise**: Suppress `asyncio` internal DEBUG messages (e.g. "Using selector: EpollSelector") by setting its logger level to WARNING in `main.py`.
- **SerpApi 400 error**: The `hl=zh-HK` language parameter caused a 400 Bad Request error because `zh-HK` is not a valid Google language code. Replaced `engine: google` + `tbm: nws` with `engine: google_news` (dedicated news engine) and removed the invalid `hl` parameter. Added `tbs: qdr:d` for today's news filter.
- **News source handling**: Updated article formatting to handle `source` as a dict (with `name` field) instead of a plain string. Format now includes `Source`, `Date`, and `Link` per article.
- **Test update**: Updated mock data in `tests/test_workflow.py` to match the new `source` dict structure. Added `test_uses_correct_serpapi_parameters` to validate the fix.

### Changed
- **config.py**: Fixed misleading comment — "Serper API" → "SerpApi" (Google Search with `tbm=nws` for news).
- **News source**: Switched from `duckduckgo_search` (DDGS) to [SerpApi SDK](https://serpapi.com/) for fetching Hong Kong hot news via Google News. Updated `app/nodes/fetch_news.py`, `tests/test_workflow.py`, `.env.example`, and project documentation.

## [Unreleased]

### Added
- **Dockerfile** — Multi-stage build (builder + production) using Python 3.11-slim. Production image runs as non-root user (`nobody`), exposes port 8080, and disables auto-reload for production use.

## [0.1.0] — 2024-07-13

### Added
- **Project scaffolding**
  - `main.py` — FastAPI entry point with root HTML endpoint and SSE `/api/stream` endpoint
  - `workflow.py` — LangGraph workflow with 3 nodes: `fetch_hot_news`, `generate_feeling`, `generate_comfort`
  - `config.py` — Environment variable loader via `python-dotenv`
  - `requirements.txt` — Python dependencies
  - `.env.example` — Environment variable template
  - `.gitignore` — Git ignore rules
- **Tests** (`tests/`)
  - `tests/test_config.py` — Config loader and default value tests
  - `tests/test_workflow.py` — Node logic tests (mocked LLM/DDG calls)
  - `tests/test_main.py` — FastAPI endpoint tests (HTTPX async)
- **Frontend** — Single-page HTML in `main.py` root endpoint displays streamed news, feeling, and comfort sections

### Design Notes
- Linear LangGraph: `fetch_hot_news → generate_feeling → generate_comfort`
- SSE streaming via `sse-starlette` + `graph.astream_events(version="v2")`
- OpenAI-compatible LLM via `langchain_openai.ChatOpenAI` with `base_url` override
- All errors are caught per-node and yielded as structured SSE error events
- Environment variables: `LLM_ENDPOINT`, `LLM_MODEL`, `LLM_PORT`, `APP_PORT`
