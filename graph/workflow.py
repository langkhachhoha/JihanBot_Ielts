"""LangGraph workflow for JihanBot v2 — Task 1/2 generate + grade."""

from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import InMemorySaver

from agents import (
    grade_and_refine_node,
    generate_essay_node,
    hitl_planning_node,
    ingest_source_node,
    refine_ideas_node,
)
from schemas.state import JihanState


def route_after_hitl(state: JihanState) -> Literal["refine", "generate", "grade"]:
    """
    After HITL planning: refine if generating with an outline; else generate or grade-only.
    """
    mode = state.get("user_mode")
    if mode == "grade_only":
        return "grade"
    if mode == "generate":
        outline = (state.get("user_outline") or "").strip()
        if outline:
            return "refine"
        return "generate"
    return "grade"


def create_jihan_graph():
    """Build and compile the JihanBot v2 graph."""
    builder = StateGraph(JihanState)

    builder.add_node("ingest_source", ingest_source_node)
    builder.add_node("hitl_planning", hitl_planning_node)
    builder.add_node("refine_ideas", refine_ideas_node)
    builder.add_node("generate_essay", generate_essay_node)
    builder.add_node("grade_and_refine", grade_and_refine_node)

    builder.add_edge(START, "ingest_source")
    builder.add_edge("ingest_source", "hitl_planning")
    builder.add_conditional_edges(
        "hitl_planning",
        route_after_hitl,
        {
            "refine": "refine_ideas",
            "generate": "generate_essay",
            "grade": "grade_and_refine",
        },
    )
    builder.add_edge("refine_ideas", "generate_essay")
    builder.add_edge("generate_essay", "grade_and_refine")
    builder.add_edge("grade_and_refine", END)

    memory = InMemorySaver()
    return builder.compile(
        checkpointer=memory,
        interrupt_before=["hitl_planning"],
    )
