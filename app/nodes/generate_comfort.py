"""
Node 3 — Generate a pastoral, scripture-based comfort response.

Uses the configured LLM (OpenAI-compatible endpoint) to respond
to the generated feelings with biblical comfort.

Runs as an async function so that model.astream() can emit
on_chat_model_stream events, which the SSE generator forwards
to the client in real-time.
"""

import logging
import traceback

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import LLM_ENDPOINT, LLM_MODEL, LLM_API_KEY

logger = logging.getLogger(__name__)

COMFORT_PROMPT = (
    "假設你是一位福音派基督教牧師, 綜合以下香港人當下的狀況和感受，你會如何用聖經經文來回應或安慰他們。請用少於250字表達。\n\n"
    "{{feeling}}"
)


async def generate_comfort(state) -> dict:
    """
    Use the LLM to generate a pastoral, scripture-based comfort response.

    Uses model.astream() so that on_chat_model_stream events are
    emitted during generation, allowing the SSE layer to stream
    tokens to the client in real-time.
    """
    logger.info("Node [generate_comfort] — calling LLM")
    logger.debug("Node [generate_comfort] — LLM config: endpoint=%s, model=%s, key_length=%d", LLM_ENDPOINT, LLM_MODEL, len(LLM_API_KEY) if LLM_API_KEY else 0)

    model = ChatOpenAI(
        base_url=LLM_ENDPOINT,
        model=LLM_MODEL,
        api_key=LLM_API_KEY,
        temperature=0.7,
    )

    messages: list[BaseMessage] = [
        SystemMessage(content="你是一位福音派基督教牧師，用聖經經文安慰他人。"),
        HumanMessage(content=COMFORT_PROMPT.replace("{{feeling}}", state.feeling)),
    ]
    logger.debug("Node [generate_comfort] — prepared %d messages for LLM call", len(messages))
    logger.debug("Node [generate_comfort] — system prompt: %s", messages[0].content)
    logger.debug("Node [generate_comfort] — user prompt (feeling preview): %.200s...", state.feeling[:200])

    try:
        logger.debug("Node [generate_comfort] — invoking LLM model via astream()...")
        chunks: list[str] = []
        async for chunk in model.astream(messages):
            content = chunk.content if hasattr(chunk, "content") else str(chunk)
            if content:
                chunks.append(content)
                logger.debug("Node [generate_comfort] — token chunk: %s", content[:50])
        comfort_text = "".join(chunks).strip()
        logger.info("Node [generate_comfort] — LLM response received (%d chars)", len(comfort_text))
        logger.debug("Node [generate_comfort] — LLM response preview: %.200s...", comfort_text[:200])
        return {"comfort": comfort_text}
    except Exception as exc:
        logger.error(
            "Node [generate_comfort] — LLM call failed: %s\n%s",
            exc,
            traceback.format_exc(),
        )
        return {"comfort": f"(Error generating comfort: {exc})"}
