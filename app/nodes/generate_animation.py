"""
Node 4 — Generate an HTML animation illustrating the comfort message.

Uses the configured LLM (OpenAI-compatible endpoint) to create a
fully self-contained HTML/CSS animation that visually represents
the pastoral comfort message. The generated HTML is saved to the
static/ folder. Only the animation URL path is streamed back to
the client — no HTML content is streamed.
"""

import logging
import os
import re
import time
import traceback

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import LLM_ENDPOINT, LLM_MODEL, LLM_API_KEY, ANIMATION_TEMPERATURE

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an expert Frontend Engineer and Creative Digital Illustrator specializing in "
    "pure HTML and CSS artwork, UI micro-interactions, and complex keyframe animations.\n\n"
    "Your task is to create a fully self-contained, highly detailed visual illustration and "
    "animation based on the user's request.\n\n"
    "### Core Technical Requirements:\n"
    "1. Single File: Deliver everything in ONE single file container. Use inline <style> blocks "
    "for the CSS.\n"
    "2. No Images/External Assets: Do NOT use external images, SVGs, or dependencies. Every "
    "shape or character must be constructed using semantic HTML elements and CSS (divs, "
    "pseudo-elements like ::before/::after, gradients, box-shadows, and border-radius).\n"
    "3. Responsive & Centered: Use Flexbox or Grid to perfectly center the illustration in the "
    "viewport (100vh). Ensure it scales gracefully using relative units (e.g., rem, em, vmin, %).\n"
    "4. Fluid Animations: Implement smooth, infinite @keyframes loops using transforms to "
    "maximize performance.\n\n"
    "### Output Format:\n"
    "Provide ONLY the raw HTML code inside standard markdown code blocks (e.g., ```html ... ```). "
    "Do not include any introductory or summary text."
)


def _strip_markdown_code_fences(html_text: str) -> str:
    """
    Remove markdown code fences (```html ... ``` or ``` ... ```) from LLM output.

    Returns the raw HTML content, stripped of surrounding whitespace.
    """
    # Match optional opening fence with language tag, content, and closing fence
    pattern = r"^```(?:html)?\s*\n?(.*?)\n?\s*```$\s*"
    cleaned = re.sub(pattern, r"\1", html_text, flags=re.DOTALL | re.MULTILINE)
    return cleaned.strip()


def _save_html(html_content: str, static_dir: str, timestamp: int) -> str:
    """
    Save the generated HTML content to the static folder.

    Returns the relative URL path (e.g. '/animation_1720000000.html').
    Raises OSError on write failure.
    """
    filename = f"animation_{timestamp}.html"
    filepath = os.path.join(static_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    logger.info("Node [generate_animation] — saved HTML animation: %s (%d bytes)", filepath, len(html_content))
    return f"/static/{filename}"


async def generate_animation(state) -> dict:
    """
    Use the LLM to generate a self-contained HTML/CSS animation
    that illustrates the pastoral comfort message.

    The generated HTML is saved to the static/ folder. The animation
    URL path is stored in the state as `animation`.

    Uses model.ainvoke() — no token streaming is emitted. The HTML
    content is saved to static/ and only the URL is returned in the
    SSE stream, so the frontend can render the animation via iframe.
    """
    logger.info("Node [generate_animation] — calling LLM")
    logger.debug(
        "Node [generate_animation] — LLM config: endpoint=%s, model=%s, "
        "comfort_length=%d",
        LLM_ENDPOINT,
        LLM_MODEL,
        len(state.comfort),
    )

    model = ChatOpenAI(
        base_url=LLM_ENDPOINT,
        model=LLM_MODEL,
        api_key=LLM_API_KEY,
        temperature=ANIMATION_TEMPERATURE,
    )

    messages: list[BaseMessage] = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Generate an HTML animation that visually illustrates the following "
                f"comfort message. The animation should be emotionally resonant and "
                f"visually engaging:\n\n{state.comfort}"
            )
        ),
    ]
    logger.debug("Node [generate_animation] — prepared %d messages for LLM call", len(messages))
    logger.debug("Node [generate_animation] — comfort preview: %.200s...", state.comfort[:200])

    try:
        logger.debug("Node [generate_animation] — invoking LLM model via ainvoke()...")
        response = await model.ainvoke(messages)
        raw_html = response.content if hasattr(response, "content") else str(response)
        logger.info("Node [generate_animation] — LLM response received (%d chars)", len(raw_html))
        logger.debug("Node [generate_animation] — LLM response preview: %.200s...", raw_html[:200])

        # Strip markdown code fences from LLM output
        html_content = _strip_markdown_code_fences(raw_html)
        logger.info("Node [generate_animation] — cleaned HTML (%d chars)", len(html_content))

        # Save to static folder
        static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")
        timestamp = int(time.time())
        animation_url = _save_html(html_content, static_dir, timestamp)
        logger.info("Node [generate_animation] — animation saved at URL: %s", animation_url)

        return {"animation": animation_url}
    except Exception as exc:
        logger.error(
            "Node [generate_animation] — failed: %s\n%s",
            exc,
            traceback.format_exc(),
        )
        return {"animation": f"(Error generating animation: {exc})"}
