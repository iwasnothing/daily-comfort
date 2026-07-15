"""
Unit tests for the SSE streaming layer.

Tests the event_generator function that bridges LangGraph events
to SSE events for the frontend.
"""

import json

import pytest

from app.streaming import NODE_TO_EVENT, event_generator


class Chunk:
    """Mock LLM token chunk with content attribute."""

    def __init__(self, content: str):
        self.content = content


def make_mock_event(event_type: str, name: str = "", data: dict | None = None):
    """Create a mock LangGraph event dict."""
    return {"event": event_type, "name": name, "data": data or {}}


def make_streaming_events(node_name: str, tokens: list[str]):
    """Create events simulating an LLM streaming call."""
    out = [make_mock_event("on_chain_start", node_name)]
    for token in tokens:
        out.append(make_mock_event(
            "on_chat_model_stream", node_name, {"chunk": Chunk(token)}
        ))
    key = node_name.replace("generate_", "")
    out.append(make_mock_event(
        "on_chain_end", node_name,
        {"output": {key: "".join(tokens)}},
    ))
    return out


def make_news_events(final_text: str):
    """Create mock events for the news node."""
    return [
        make_mock_event("on_chain_start", "fetch_hot_news"),
        make_mock_event(
            "on_chain_end", "fetch_hot_news",
            {"output": {"hot_news": final_text}},
        ),
    ]


def make_graph_with_events(events: list[dict]):
    """Create a mock compiled graph that yields the given events."""
    async def astream_events(*_args, **_kwargs):
        for ev in events:
            yield ev

    mock = type("MockGraph", (), {})()
    mock.astream_events = astream_events
    return mock


def make_graph_with_empty_events():
    """Create a mock compiled graph with no events."""
    async def astream_events(*_args, **_kwargs):
        return
        yield  # makes this an async generator

    mock = type("MockGraph", (), {})()
    mock.astream_events = astream_events
    return mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_chunk_event_format():
    """Verify that streaming chunk events have correct SSE format."""
    tokens = ["這", "是", "測試"]
    graph = make_graph_with_events(make_streaming_events("generate_feeling", tokens))

    yielded = []
    async for event in event_generator(graph):
        yielded.append(event)

    feeling_events = [e for e in yielded if e.get("event") == "feeling"]
    assert len(feeling_events) >= 2  # at least one chunk + one final

    first_data = json.loads(feeling_events[0]["data"])
    assert "chunk" in first_data
    assert "content" in first_data
    assert first_data["chunk"] == "這"
    assert first_data["content"] == "這"


@pytest.mark.asyncio
async def test_sse_accumulated_text_in_chunks():
    """Verify that accumulated text builds up across chunk events."""
    tokens = ["A", "B", "C"]
    graph = make_graph_with_events(make_streaming_events("generate_feeling", tokens))

    yielded = []
    async for event in event_generator(graph):
        yielded.append(event)

    feeling_events = [e for e in yielded if e.get("event") == "feeling"]
    chunk_events = feeling_events[:-1]  # skip last (final content)

    assert len(chunk_events) == 3
    assert json.loads(chunk_events[0]["data"])["content"] == "A"
    assert json.loads(chunk_events[1]["data"])["content"] == "AB"
    assert json.loads(chunk_events[2]["data"])["content"] == "ABC"


@pytest.mark.asyncio
async def test_sse_final_event_has_complete_text():
    """Verify that the final node event contains the complete text."""
    tokens = ["這", "是", "完整", "的", "測試"]
    graph = make_graph_with_events(make_streaming_events("generate_feeling", tokens))

    yielded = []
    async for event in event_generator(graph):
        yielded.append(event)

    feeling_events = [e for e in yielded if e.get("event") == "feeling"]
    last_data = json.loads(feeling_events[-1]["data"])
    assert last_data["content"] == "這是完整的測試"


@pytest.mark.asyncio
async def test_sse_news_event_format():
    """Verify that the news event has correct SSE format."""
    graph = make_graph_with_events(make_news_events("Test news content"))

    yielded = []
    async for event in event_generator(graph):
        yielded.append(event)

    news_events = [e for e in yielded if e.get("event") == "news"]
    assert len(news_events) == 1
    data = json.loads(news_events[0]["data"])
    assert data["content"] == "Test news content"


@pytest.mark.asyncio
async def test_sse_error_event_on_exception():
    """Verify that exceptions produce error SSE events."""
    async def astream_events(*_args, **_kwargs):
        raise RuntimeError("LLM connection failed")
        yield  # never reached

    mock = type("MockGraph", (), {})()
    mock.astream_events = astream_events

    yielded = []
    async for event in event_generator(mock):
        yielded.append(event)

    error_events = [e for e in yielded if e.get("event") == "error"]
    assert len(error_events) == 1
    error_data = json.loads(error_events[0]["data"])
    assert error_data["node"] == "workflow"
    assert "LLM connection failed" in error_data["message"]


@pytest.mark.asyncio
async def test_sse_close_event_after_error():
    """Verify that a close event follows the error event."""
    async def astream_events(*_args, **_kwargs):
        raise RuntimeError("connection lost")
        yield  # never reached

    mock = type("MockGraph", (), {})()
    mock.astream_events = astream_events

    yielded = []
    async for event in event_generator(mock):
        yielded.append(event)

    close_events = [e for e in yielded if e.get("event") == "close"]
    assert len(close_events) == 1


@pytest.mark.asyncio
async def test_node_to_event_mapping():
    """Verify the NODE_TO_EVENT mapping is complete."""
    expected = {
        "generate_feeling": "feeling",
        "generate_comfort": "comfort",
        "generate_animation": "animation",
        "fetch_hot_news": "news",
    }
    assert NODE_TO_EVENT == expected


@pytest.mark.asyncio
async def test_sse_event_generator_empty_graph():
    """Verify that an empty event stream produces a done event."""
    graph = make_graph_with_empty_events()

    yielded = []
    async for event in event_generator(graph):
        yielded.append(event)

    done_events = [e for e in yielded if e.get("event") == "done"]
    assert len(done_events) == 1
    done_data = json.loads(done_events[0]["data"])
    assert done_data["hot_news"] == ""
    assert done_data["feeling"] == ""
    assert done_data["comfort"] == ""
    assert done_data["animation"] == ""


def make_animation_events(
    anim_url: str, include_streaming_tokens: bool = False, tokens: list[str] | None = None
):
    """Create mock events for the animation node.

    By default emits only on_chain_start + on_chain_end (non-streaming).
    Set include_streaming_tokens=True to also emit on_chat_model_stream events.
    """
    if tokens is None:
        tokens = ["<html>", "<body>", "</body>", "</html>"]
    out = [make_mock_event("on_chain_start", "generate_animation")]
    if include_streaming_tokens:
        for token in tokens:
            out.append(make_mock_event(
                "on_chat_model_stream", "generate_animation", {"chunk": Chunk(token)}
            ))
    out.append(make_mock_event(
        "on_chain_end", "generate_animation",
        {"output": {"animation": anim_url}},
    ))
    return out


@pytest.mark.asyncio
async def test_sse_done_event_has_all_fields():
    """Verify that the done event contains all four fields."""
    events = (
        make_news_events("News text")
        + make_streaming_events("generate_feeling", ["F1", "F2"])
        + make_streaming_events("generate_comfort", ["C1", "C2"])
        + make_animation_events("/animation_12345.html")
    )
    graph = make_graph_with_events(events)

    yielded = []
    async for event in event_generator(graph):
        yielded.append(event)

    done_events = [e for e in yielded if e.get("event") == "done"]
    assert len(done_events) == 1
    done_data = json.loads(done_events[0]["data"])
    assert done_data["hot_news"] == "News text"
    assert done_data["feeling"] == "F1F2"
    assert done_data["comfort"] == "C1C2"
    assert done_data["animation"] == "/animation_12345.html"


@pytest.mark.asyncio
async def test_sse_animation_event():
    """Verify that the animation event yields the animation URL."""
    events = make_animation_events("/animation_99999.html")
    graph = make_graph_with_events(events)

    yielded = []
    async for event in event_generator(graph):
        yielded.append(event)

    animation_events = [e for e in yielded if e.get("event") == "animation"]
    assert len(animation_events) == 1
    data = json.loads(animation_events[0]["data"])
    assert data["url"] == "/animation_99999.html"


@pytest.mark.asyncio
async def test_animation_node_skips_streaming_tokens():
    """Verify that streaming tokens for generate_animation are NOT emitted as SSE events.

    The animation node saves HTML to a file and only returns the URL via on_chain_end.
    Streaming HTML tokens would flood the SSE feed with large markup payloads.
    """
    large_html = "<html><body>" + "<div>" * 500 + "</body></html>"
    tokens = [large_html[:100], large_html[100:200], large_html[200:300], large_html[300:]]
    events = make_animation_events(
        "/animation_test.html", include_streaming_tokens=True, tokens=tokens
    )
    graph = make_graph_with_events(events)

    yielded = []
    async for event in event_generator(graph):
        yielded.append(event)

    # Only the final on_chain_end should produce an "animation" SSE event.
    # Streaming token chunks must be suppressed.
    animation_events = [e for e in yielded if e.get("event") == "animation"]
    assert len(animation_events) == 1
    data = json.loads(animation_events[0]["data"])
    assert data["url"] == "/animation_test.html"

    # Verify no streaming chunk events were emitted for animation
    for event in animation_events[:-1]:
        parsed = json.loads(event["data"])
        assert "chunk" not in parsed, (
            f"Unexpected streaming chunk in animation event: {parsed}"
        )
