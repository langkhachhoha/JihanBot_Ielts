"""HITL node_1: human supplies mode, band, outline, and/or essay before routing."""

from langgraph.types import StreamWriter

from schemas.state import JihanState


def hitl_planning_node(
    state: JihanState,
    *,
    writer: StreamWriter,
) -> dict:
    """
    Runs after the client resumes from interrupt_before this node.
    State must already contain user_mode, target_band, and optional outline/essay (via update_state).
    """
    writer("📋 Planning inputs applied — continuing pipeline...")
    mode = state.get("user_mode")
    band = state.get("target_band", "")
    writer(f"   mode={mode}, target_band={band}")
    return {"human_review_planning": True}
