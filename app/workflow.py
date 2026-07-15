"""
LangGraph workflow — graph construction and compilation.

Assembles the three workflow nodes into a compiled LangGraph graph.
The compiled graph is built lazily at request time, not at import.
"""

import logging

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledGraph

from app.models import ComfortState
from app.nodes import fetch_hot_news, generate_feeling, generate_comfort, generate_animation

logger = logging.getLogger(__name__)


def build_graph() -> CompiledGraph:
    """
    Build and compile the LangGraph state graph.

    Topology: start → fetch_hot_news → generate_feeling → generate_comfort → generate_animation → end
    """
    logger.info("Building LangGraph workflow (4 nodes)")
    logger.debug("Workflow nodes: fetch_hot_news -> generate_feeling -> generate_comfort -> generate_animation")

    workflow = StateGraph(ComfortState)

    # Add nodes
    logger.debug("Adding node: fetch_hot_news")
    workflow.add_node("fetch_hot_news", fetch_hot_news)
    logger.debug("Adding node: generate_feeling")
    workflow.add_node("generate_feeling", generate_feeling)
    logger.debug("Adding node: generate_comfort")
    workflow.add_node("generate_comfort", generate_comfort)
    logger.debug("Adding node: generate_animation")
    workflow.add_node("generate_animation", generate_animation)

    # Define edges
    logger.debug("Adding edge: fetch_hot_news -> generate_feeling")
    workflow.add_edge("fetch_hot_news", "generate_feeling")
    logger.debug("Adding edge: generate_feeling -> generate_comfort")
    workflow.add_edge("generate_feeling", "generate_comfort")
    logger.debug("Adding edge: generate_comfort -> generate_animation")
    workflow.add_edge("generate_comfort", "generate_animation")

    # Set entry and exit points
    logger.debug("Setting entry point: fetch_hot_news, exit point: END")
    workflow.set_entry_point("fetch_hot_news")
    workflow.add_edge("generate_animation", END)

    compiled = workflow.compile()
    logger.info("LangGraph workflow compiled successfully")
    return compiled
