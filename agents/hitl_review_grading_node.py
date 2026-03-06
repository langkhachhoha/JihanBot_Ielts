"""HITL Node: Human-in-the-Loop review for grading feedback."""

from langgraph.types import StreamWriter, interrupt

from schemas.state import JihanState


def hitl_review_grading_node(
    state: JihanState,
    *,
    writer: StreamWriter,
) -> dict:
    """
    Human-in-the-Loop node for reviewing and editing grading feedback.
    This node interrupts execution to allow human review after essay grading.
    """
    writer("👤 Human Review: Grading feedback ready for review...")
    
    grading_feedback = state.get("grading_feedback")
    essay = state.get("essay", "")
    
    if essay:
        writer("\n" + "=" * 60)
        writer("📝 CURRENT ESSAY")
        writer("=" * 60)
        writer(f"\n{essay}\n")
        writer("=" * 60)
    
    if grading_feedback:
        writer("\n" + "=" * 60)
        writer("📋 GRADING FEEDBACK FOR REVIEW")
        writer("=" * 60)
        
        if hasattr(grading_feedback, "passed"):
            status = "✅ PASSED" if grading_feedback.passed else "❌ NEEDS REVISION"
            writer(f"\n[STATUS] {status}\n")
        
        if hasattr(grading_feedback, "overall_score"):
            writer(f"[OVERALL SCORE] {grading_feedback.overall_score}\n")
        
        if hasattr(grading_feedback, "task_achievement_feedback") and grading_feedback.task_achievement_feedback:
            writer(f"[TASK ACHIEVEMENT]\n{grading_feedback.task_achievement_feedback}\n")
        
        if hasattr(grading_feedback, "coherence_cohesion_feedback") and grading_feedback.coherence_cohesion_feedback:
            writer(f"[COHERENCE & COHESION]\n{grading_feedback.coherence_cohesion_feedback}\n")
        
        if hasattr(grading_feedback, "lexical_resource_feedback") and grading_feedback.lexical_resource_feedback:
            writer(f"[LEXICAL RESOURCE]\n{grading_feedback.lexical_resource_feedback}\n")
        
        if hasattr(grading_feedback, "grammatical_range_feedback") and grading_feedback.grammatical_range_feedback:
            writer(f"[GRAMMATICAL RANGE]\n{grading_feedback.grammatical_range_feedback}\n")
        
        if hasattr(grading_feedback, "suggestion") and grading_feedback.suggestion:
            writer(f"[SUGGESTIONS]\n{grading_feedback.suggestion}\n")
        
        writer("=" * 60)
    
    # Interrupt execution and wait for human input
    # The main.py will handle the user input and update the state
    writer("⏸️  Workflow paused. Waiting for human review...")
    interrupt("Waiting for human to review and potentially edit grading feedback")
    
    writer("▶️  Resuming workflow with reviewed feedback...")
    
    # Mark that human review occurred
    return {"human_review_grading": True}
