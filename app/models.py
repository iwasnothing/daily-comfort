"""
Pydantic models shared across the workflow.

Defines the state schema that flows through all LangGraph nodes.
"""

from pydantic import BaseModel, Field


class ComfortState(BaseModel):
    """Shared state passed through all workflow nodes."""

    hot_news: str = Field(
        default="",
        description="Formatted hot news summary from Hong Kong.",
    )
    feeling: str = Field(
        default="",
        description="LLM-generated feeling/emotion text from a Hong Kong person's perspective.",
    )
    comfort: str = Field(
        default="",
        description="LLM-generated pastoral comfort response with scripture.",
    )
    animation: str = Field(
        default="",
        description="URL path to the generated HTML animation file (e.g. '/animation_1234567890.html').",
    )
