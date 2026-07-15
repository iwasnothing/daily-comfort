"""
SSE event generator for the Daily Comfort workflow.

Extracts streaming events from the LangGraph graph and yields them
as structured dictionaries for FastAPI's EventSourceResponse.
"""

import json
import logging
import traceback
from collections.abc import AsyncGenerator

from sse_starlette.sse import EventSourceResponse

from app.workflow import build_graph, ComfortState

logger = logging.getLogger(__name__)

# Map LangGraph node names → SSE event names used by the frontend
NODE_TO_EVENT = {
    "generate_feeling": "feeling",
    "generate_comfort": "comfort",
    "generate_animation": "animation",
    "fetch_hot_news": "news",
}


async def event_generator(
    graph,
    workflow_node: str = "",
) -> AsyncGenerator[dict, None]:
    """Generate SSE events from the LangGraph workflow stream.

    Args:
        graph: Compiled LangGraph workflow graph.
        workflow_node: Deprecated. Kept for compatibility.

    Yields:
        SSE event dicts with 'event' and 'data' keys.
    """
    try:
        state = ComfortState()
        logger.debug("Streaming: initialized ComfortState, starting astream_events loop")

        # Track workflow state from node outputs
        state_updates = {}

        # Track which workflow node is currently running an LLM call
        current_workflow_node = None

        # Track accumulated text for the current streaming node
        accumulated_text = ""

        async for event in graph.astream_events(
            state.model_dump(),
            version="v2",
        ):
            event_type = event.get("event", "")
            node_name = event.get("name", "unknown")

            # Track which workflow node started an LLM call
            if event_type == "on_chain_start" and node_name in NODE_TO_EVENT:
                current_workflow_node = node_name
                accumulated_text = ""
                logger.debug("Streaming: workflow node started: %s", node_name)

            # Handle streaming token chunks from LLM
            elif event_type == "on_chat_model_stream":
                # Skip streaming tokens for the generate_animation node.
                # The animation node saves HTML to a file and returns only the
                # URL via on_chain_end — streaming HTML tokens would flood the
                # SSE feed with thousands of characters of markup.
                if current_workflow_node == "generate_animation":
                    continue
                # Map LLM events to the current workflow node
                event_name = NODE_TO_EVENT.get(
                    current_workflow_node, current_workflow_node
                ) if current_workflow_node else node_name
                chunk = event.get("data", {}).get("chunk", None)
                if chunk is not None:
                    content = (
                        chunk.content if hasattr(chunk, "content") else str(chunk)
                    )
                    if content:
                        accumulated_text += content
                        yield {"event": event_name, "data": json.dumps(
                            {"chunk": content, "content": accumulated_text},
                            ensure_ascii=False,
                        )}

            # Handle node completion
            elif event_type == "on_chain_end":
                result = event.get("data", {}).get("output", {})
                event_name = NODE_TO_EVENT.get(node_name, node_name)

                # Capture state updates from node outputs
                if result and isinstance(result, dict):
                    state_updates.update(result)

                if event_name == "news" and result:
                    news_text = result.get("hot_news", "")
                    logger.debug(
                        "Streaming: [news] node completed (%d chars)", len(news_text)
                    )
                    yield {
                        "event": "news",
                        "data": json.dumps({"content": news_text}, ensure_ascii=False),
                    }
                    current_workflow_node = None

                elif event_name == "feeling" and result:
                    feeling_text = result.get("feeling", "")
                    logger.debug(
                        "Streaming: [feeling] node completed (%d chars)",
                        len(feeling_text),
                    )
                    yield {
                        "event": "feeling",
                        "data": json.dumps({"content": feeling_text}, ensure_ascii=False),
                    }
                    current_workflow_node = None

                elif event_name == "comfort" and result:
                    comfort_text = result.get("comfort", "")
                    logger.debug(
                        "Streaming: [comfort] node completed (%d chars)",
                        len(comfort_text),
                    )
                    yield {
                        "event": "comfort",
                        "data": json.dumps({"content": comfort_text}, ensure_ascii=False),
                    }
                    current_workflow_node = None

                elif event_name == "animation" and result:
                    animation_url = result.get("animation", "")
                    logger.debug(
                        "Streaming: [animation] node completed, url=%s",
                        animation_url,
                    )
                    yield {
                        "event": "animation",
                        "data": json.dumps({"url": animation_url}, ensure_ascii=False),
                    }
                    current_workflow_node = None

            # Log all other event types for debugging
            else:
                logger.debug("Streaming: event_type=%s (ignored)", event_type)

        # Send final complete payload from captured state updates
        final_data = {
            "hot_news": state_updates.get("hot_news", ""),
            "feeling": state_updates.get("feeling", ""),
            "comfort": state_updates.get("comfort", ""),
            "animation": state_updates.get("animation", ""),
        }
        logger.debug(
            "Streaming: sending final done event with state: hot_news=%d chars, "
            "feeling=%d chars, comfort=%d chars, animation=%s",
            len(final_data["hot_news"]),
            len(final_data["feeling"]),
            len(final_data["comfort"]),
            final_data["animation"],
        )
        yield {"event": "done", "data": json.dumps(final_data, ensure_ascii=False)}

    except Exception as exc:
        logger.error("SSE stream error: %s\n%s", exc, traceback.format_exc())
        logger.debug("Streaming exception details: %s", repr(exc))
        # Yield error event first, then explicitly close the connection
        # so the browser EventSource does NOT auto-reconnect and re-trigger the workflow.
        yield {
            "event": "error",
            "data": json.dumps(
                {"node": "workflow", "message": str(exc)}, ensure_ascii=False
            ),
        }
        yield {"event": "close"}


async def stream_comfort():
    """
    Create an EventSourceResponse that streams the workflow results.

    Events:
      - news      : Formatted hot news
      - feeling   : LLM-generated feeling/emotion
      - comfort   : LLM-generated pastoral comfort
      - done      : Final complete payload (JSON)
      - error     : Error event with details
    """
    logger.info("SSE stream request received, building workflow graph")

    # Build the LangGraph workflow graph lazily at request time
    graph = build_graph()

    return EventSourceResponse(event_generator(graph))
