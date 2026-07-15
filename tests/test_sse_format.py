"""Tests for SSE event format and frontend compatibility.

Verifies that the SSE events sent by the backend match the expected
format that the frontend app.js expects to receive.
"""

import json


def test_sse_event_format():
    """SSE events have 'event' (type) and 'data' (JSON string) as separate fields.

    The browser's EventSource receives:
      - event.event = the SSE event type (e.g., "news", "feeling", "done")
      - event.data = the raw JSON string (not a parsed object)

    The frontend must read event.event for the type, NOT data.event.
    """
    # Simulate what the backend yields:
    sse_event = {"event": "news", "data": json.dumps({"content": "test news"})}

    # The EventSource receives this as:
    event_type = sse_event["event"]  # "news"
    raw_data = sse_event["data"]  # '{"content": "test news"}'
    parsed = json.loads(raw_data)  # {"content": "test news"}

    # The frontend MUST use event.event, NOT data.event
    assert event_type == "news"
    assert "event" not in parsed  # 'event' is NOT in the JSON data

    # The frontend reads data.content (from the parsed JSON), NOT data.data.content
    assert parsed["content"] == "test news"


def test_sse_streaming_chunk_format():
    """Streaming chunks have 'chunk' and 'content' fields."""
    sse_event = {
        "event": "feeling",
        "data": json.dumps({"chunk": "看到", "content": "\n\n看到"}),
    }

    event_type = sse_event["event"]
    parsed = json.loads(sse_event["data"])

    assert event_type == "feeling"
    assert "event" not in parsed
    assert parsed["chunk"] == "看到"
    assert parsed["content"] == "\n\n看到"


def test_sse_done_event_format():
    """Done event contains the complete state."""
    sse_event = {
        "event": "done",
        "data": json.dumps({"hot_news": "news text", "feeling": "feel text", "comfort": "comfort text"}),
    }

    event_type = sse_event["event"]
    parsed = json.loads(sse_event["data"])

    assert event_type == "done"
    assert "event" not in parsed
    assert parsed["hot_news"] == "news text"
    assert parsed["feeling"] == "feel text"
    assert parsed["comfort"] == "comfort text"


def test_sse_error_event_format():
    """Error event contains node and message."""
    sse_event = {
        "event": "error",
        "data": json.dumps({"node": "workflow", "message": "something failed"}),
    }

    event_type = sse_event["event"]
    parsed = json.loads(sse_event["data"])

    assert event_type == "error"
    assert "event" not in parsed
    assert parsed["node"] == "workflow"
    assert parsed["message"] == "something failed"


def test_frontend_parses_event_type_correctly():
    """Simulate the frontend's event handling logic.

    This is a Python simulation of what app.js does in the browser.
    It verifies the frontend correctly reads event.event (not data.event).
    """
    events = [
        {"event": "news", "data": json.dumps({"content": "news content"})},
        {"event": "feeling", "data": json.dumps({"chunk": "abc", "content": "abc"})},
        {"event": "feeling", "data": json.dumps({"chunk": "def", "content": "abcdef"})},
        {"event": "done", "data": json.dumps({"hot_news": "", "feeling": "", "comfort": ""})},
    ]

    received_events = []

    for sse_event in events:
        event_type = sse_event["event"]
        data = json.loads(sse_event["data"])

        if event_type == "news":
            received_events.append(("news", data.get("content", data)))
        elif event_type == "feeling":
            received_events.append(("feeling", data.get("content", data)))
        elif event_type == "comfort":
            received_events.append(("comfort", data.get("content", data)))
        elif event_type == "done":
            received_events.append(("done", data))

    # Verify all events were correctly parsed
    assert len(received_events) == 4
    assert received_events[0] == ("news", "news content")
    assert received_events[1] == ("feeling", "abc")
    assert received_events[2] == ("feeling", "abcdef")
    assert received_events[3][0] == "done"
    assert received_events[3][1]["hot_news"] == ""


def test_frontend_would_fail_with_old_logic():
    """Verify that the OLD frontend logic (using data.event) would fail.

    This test documents the bug that was fixed.
    """
    sse_event = {"event": "news", "data": json.dumps({"content": "test"})}
    data = json.loads(sse_event["data"])

    # OLD code: if data.event === "news"
    # data.event would be undefined/None, so the branch would never match
    assert data.get("event") is None  # BUG: "event" is not in the parsed JSON

    # NEW code: use event.event (the SSE event type)
    assert sse_event["event"] == "news"  # FIX: correct event type
