"""LangGraph workflow for JihanBot IELTS Writing Task 1 pipeline."""

from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import InMemorySaver

from schemas.state import JihanState
from agents import (
    extract_question_node,
    extract_features_node,
    verify_extraction_node,
    write_essay_node,
    grade_essay_node,
)


def _route_after_verification(state: JihanState) -> str:
    """Route from node_3: go to node_4 if verified or max retries, else back to node_2."""
    if state.get("extraction_verified", False):
        return "write_essay"
    return "extract_features"


def _route_after_grading(state: JihanState):
    """Route from node_5: go to END if passed or max retries, else back to node_4."""
    if state.get("grading_passed", False):
        return END
    return "write_essay"


def create_jihan_graph():
    """Build and compile the JihanBot graph."""
    builder = StateGraph(JihanState)

    # Add nodes
    builder.add_node("extract_question", extract_question_node)
    builder.add_node("extract_features", extract_features_node)
    builder.add_node("verify_extraction", verify_extraction_node)
    builder.add_node("write_essay", write_essay_node)
    builder.add_node("grade_essay", grade_essay_node)

    # Add edges
    builder.add_edge(START, "extract_question")
    builder.add_edge("extract_question", "extract_features")
    builder.add_edge("extract_features", "verify_extraction")
    builder.add_conditional_edges("verify_extraction", _route_after_verification)
    # builder.add_edge("extract_features", "write_essay")
    builder.add_edge("write_essay", "grade_essay")
    builder.add_conditional_edges("grade_essay", _route_after_grading)

    # Compile with checkpointing for state persistence
    memory = InMemorySaver()
    return builder.compile(checkpointer=memory)
