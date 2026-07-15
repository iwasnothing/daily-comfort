"""
Node 2 — Generate a Hong Kong person's emotional response to the news.

Uses the configured LLM (OpenAI-compatible endpoint) to interpret
the hot news from a local resident's perspective.

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

FEELING_PROMPT = (
    "假設你是香港人面對以下的香港新聞你會有什麼感受？請用少於250字表達。\n\n"
    "{{hot_news}}"
)


async def generate_feeling(state) -> dict:
    """
    Use the LLM to generate a Hong Kong person's emotional response
    to the hot news.

    Uses model.astream() so that on_chat_model_stream events are
    emitted during generation, allowing the SSE layer to stream
    tokens to the client in real-time.
    """
    logger.info("Node [generate_feeling] — calling LLM")
    logger.debug("Node [generate_feeling] — LLM config: endpoint=%s, model=%s, key_length=%d", LLM_ENDPOINT, LLM_MODEL, len(LLM_API_KEY) if LLM_API_KEY else 0)

    model = ChatOpenAI(
        base_url=LLM_ENDPOINT,
        model=LLM_MODEL,
        api_key=LLM_API_KEY,
        temperature=0.7,
    )

    messages: list[BaseMessage] = [
        SystemMessage(content="你是一位香港居民，對新聞有真誠的感受。"),
        HumanMessage(content=FEELING_PROMPT.replace("{{hot_news}}", state.hot_news)),
    ]
    logger.debug("Node [generate_feeling] — prepared %d messages for LLM call", len(messages))
    logger.debug("Node [generate_feeling] — system prompt: %s", messages[0].content)
    logger.debug("Node [generate_feeling] — user prompt (news preview): %.200s...", state.hot_news[:200])

    try:
        logger.debug("Node [generate_feeling] — invoking LLM model via astream()...")
        chunks: list[str] = []
        async for chunk in model.astream(messages):
            content = chunk.content if hasattr(chunk, "content") else str(chunk)
            if content:
                chunks.append(content)
        feeling_text = "".join(chunks).strip()
        logger.info("Node [generate_feeling] — LLM response received (%d chars)", len(feeling_text))
        logger.debug("Node [generate_feeling] — LLM response preview: %.200s...", feeling_text[:200])
        return {"feeling": feeling_text}
    except Exception as exc:
        logger.error(
            "Node [generate_feeling] — LLM call failed: %s\n%s",
            exc,
            traceback.format_exc(),
        )
        return {"feeling": f"(Error generating feeling: {exc})"}
