"""HITL Node: Human-in-the-Loop review for extracted features."""

from langgraph.types import StreamWriter, interrupt

from schemas.state import JihanState


def hitl_review_features_node(
    state: JihanState,
    *,
    writer: StreamWriter,
) -> dict:
    """
    Human-in-the-Loop node for reviewing and editing extracted features.
    This node interrupts execution to allow human review before verification.
    """
    writer("👤 Human Review: Extracted features ready for review...")
    
    extracted_features = state.get("extracted_features")
    
    if extracted_features:
        writer("\n" + "=" * 60)
        writer("📊 EXTRACTED FEATURES FOR REVIEW")
        writer("=" * 60)
        
        if hasattr(extracted_features, "overview"):
            writer(f"\n[OVERVIEW]\n{extracted_features.overview}\n")
        if hasattr(extracted_features, "paragraph_1"):
            writer(f"[PARAGRAPH 1]\n{extracted_features.paragraph_1}\n")
        if hasattr(extracted_features, "paragraph_2"):
            writer(f"[PARAGRAPH 2]\n{extracted_features.paragraph_2}\n")
        if hasattr(extracted_features, "grouping_logic"):
            writer(f"[GROUPING LOGIC]\n{extracted_features.grouping_logic}\n")
        
        writer("=" * 60)
    
    # Interrupt execution and wait for human input
    # The main.py will handle the user input and update the state
    writer("⏸️  Workflow paused. Waiting for human review...")
    interrupt("Waiting for human to review and potentially edit extracted features")
    
    writer("▶️  Resuming workflow with reviewed features...")
    
    # Mark that human review occurred
    return {"human_review_features": True}
