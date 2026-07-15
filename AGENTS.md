## Overview

Daily Comfort is a Python FastAPI server that runs a LangGraph workflow to:
1. Fetch today's trending Hong Kong news via SerpApi (Google Search with `tbm=nws`)
2. Generate a Hong Kong resident's emotional response using an LLM
3. Generate a pastoral, scripture-based comfort response using the same LLM
4. Generate an HTML/CSS animation that visually illustrates the comfort message

Results are streamed back to the frontend via SSE (Server-Sent Events) using `sse-starlette` and `graph.astream_events(version="v2")`.

## Architecture

```
main.py (FastAPI entry point)
  ├── GET /           → serves static/index.html
  ├── GET /api/stream → SSE stream (delegates to app.streaming.stream_comfort)
  └── GET /health     → health check

app/
  ├── workflow.py     → LangGraph graph construction (build_graph → CompiledGraph, called lazily at request time)
  ├── streaming.py    → SSE event generator (stream_comfort → builds graph via build_graph() → EventSourceResponse)
  ├── models.py       → Pydantic ComfortState (hot_news, feeling, comfort, animation)
  └── nodes/
        ├── fetch_news.py          → Node 1: SerpApi Google News search
        ├── generate_feeling.py    → Node 2: LLM → Hong Kong person's feelings
        ├── generate_comfort.py    → Node 3: LLM → pastoral comfort with scripture
        └── generate_animation.py  → Node 4: LLM → HTML/CSS animation illustrating comfort

config.py         → Environment variable loader (python-dotenv)
static/index.html → Single-page frontend with table layout
static/app.js     → SSE client (EventSource)
```

## LangGraph Workflow

Topology: `start → fetch_hot_news → generate_feeling → generate_comfort → generate_animation → end`

All nodes share a `ComfortState` Pydantic model. Each node returns a `dict` that LangGraph merges into the state.

**Lazy compilation**: The graph is built only when `/api/stream` is called, not at server startup. `app/streaming.py` imports `build_graph()` and calls it inside `stream_comfort()` before starting the event loop.

### Logging

The root logger is set to `DEBUG` level in `main.py` with a formatted console handler (`%(asctime)s [%(levelname)s] %(name)s — %(message)s`). Every API request, LLM call, SerpApi call, and LangGraph node transition emits debug-level log messages. HTTP client libraries (urllib3, httpcore, openai, httpx) also emit debug logs showing request/response details.

### Node 1 — `fetch_hot_news` (`app/nodes/fetch_news.py`)

Uses the SerpApi SDK to search Google News:

```python
client = serpapi.Client(api_key=SERPAPI_API_KEY)
results = client.search({
    "engine": "google",
    "tbm": "nws",
    "q": "Hong Kong news",
    "gl": "hk",
    "hl": "zh-HK",
    "tbs": "qdr:d",
})
news_results = results.get("news_results", [])
```

- Limits to top 5 results (`MAX_RESULTS = 5`)
- Formats each article as: `Title` + `Link` + separator line
- Error handling: returns descriptive placeholder strings on failure

### Node 2 — `generate_feeling` (`app/nodes/generate_feeling.py`)

Calls an OpenAI-compatible LLM via `langchain_openai.ChatOpenAI` with:
- System prompt: "你是一位香港居民，對新聞有真誠的感受。"
- User prompt: "假設你是香港人面對以下的香港新聞你會有什麼感受？請用少於250字表達。" + `state.hot_news`
- Configured via env: `LLM_ENDPOINT`, `LLM_MODEL`, `LLM_API_KEY`

### Node 3 — `generate_comfort` (`app/nodes/generate_comfort.py`)

Calls the same LLM with:
- System prompt: "你是一位福音派基督教牧師，用聖經經文安慰他人。"
- User prompt: "假設你是一位福音派基督教牧師面對以下香港人的感受，你會如何用聖經經文來回應或安慰他們。請用少於250字表達。" + `state.feeling`

### Node 4 — `generate_animation` (`app/nodes/generate_animation.py`)

Calls the LLM with a system prompt that instructs it to create a fully self-contained HTML/CSS animation.
- System prompt: Expert Frontend Engineer persona with technical requirements for single-file HTML, no external assets, responsive centering, and fluid animations
- User prompt: "Generate an HTML animation that visually illustrates the following comfort message..." + `state.comfort`
- Strips markdown code fences from LLM output
- Saves generated HTML to `static/animation_{timestamp}.html`
- Returns `{"animation": "/animation_{timestamp}.html"}` in state
- The frontend renders the animation as an `<iframe>` in a dedicated container below the table

## SSE Streaming (`app/streaming.py`)

`stream_comfort()` creates an `EventSourceResponse` that yields events from `comfort_graph.astream_events(version="v2")`:

| Event Name | Source                                    |
|------------|-------------------------------------------|
| `news`     | Node 1 output (formatted hot news)        |
| `feeling`  | Node 2 LLM streaming chunks + final output |
| `comfort`  | Node 3 LLM streaming chunks + final output |
| `animation`| Node 4 output (animation URL path)        |
| `done`     | Final complete JSON payload (all 4 fields) |
| `error`    | Exception details                         |

`NODE_TO_EVENT` map: `{"generate_feeling": "feeling", "generate_comfort": "comfort", "generate_animation": "animation", "fetch_hot_news": "news"}`

- For LLM streaming (`on_chat_model_stream`): yields token chunks with the node's event name
- For node completion (`on_chain_end`): yields the final text output
- Final `done` event includes the full state JSON

## Configuration (`config.py`)

All values loaded from environment variables (with defaults) via `python-dotenv`:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_ENDPOINT` | `http://localhost:8000/v1` | OpenAI-compatible API base URL |
| `LLM_MODEL` | `Ornith-1.0-35B` | Model identifier |
| `LLM_PORT` | `8000` | Upstream LLM server port (informational) |
| `LLM_API_KEY` | `nokey` | API key for the LLM server |
| `SERPAPI_API_KEY` | `""` | SerpApi key (required for news) |
| `APP_PORT` | `8080` | FastAPI server port |
| `ANIMATION_TEMPERATURE` | `0.8` | LLM temperature for animation generation (creative) |

## Dependencies (`requirements.txt`)

- `fastapi`, `uvicorn[standard]` — Web framework
- `sse-starlette` — SSE support for FastAPI
- `langgraph` — LangGraph workflow engine
- `langchain-openai` — OpenAI-compatible LLM adapter
- `python-dotenv` — `.env` file loading
- `pydantic` — State model definition
- `serpapi` — SerpApi SDK for news search
- `pytest`, `httpx` — Testing

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **daily-comfort** (202 symbols, 312 relationships, 3 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({search_query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/daily-comfort/context` | Codebase overview, check index freshness |
| `gitnexus://repo/daily-comfort/clusters` | All functional areas |
| `gitnexus://repo/daily-comfort/processes` | All execution flows |
| `gitnexus://repo/daily-comfort/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
