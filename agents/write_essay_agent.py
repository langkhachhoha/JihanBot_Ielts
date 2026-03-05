"""Node 4: Write full IELTS Writing Task 1 essay according to band score."""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import StreamWriter

from config import get_text_model
from schemas.state import JihanState, ExtractedFeatures, GradingFeedback


def _grading_needs_revision(fb) -> bool:
    """Check if grading_feedback indicates revision is needed."""
    if fb is None:
        return False
    return not (fb.passed if hasattr(fb, "passed") else (fb.get("passed", True) if isinstance(fb, dict) else True))


def _format_grading_feedback(fb) -> str:
    """Format GradingFeedback for the revision prompt."""
    if fb is None:
        return ""
    parts = []
    if hasattr(fb, "task_achievement_feedback") and fb.task_achievement_feedback:
        parts.append(f"Task Achievement: {fb.task_achievement_feedback}")
    if hasattr(fb, "coherence_cohesion_feedback") and fb.coherence_cohesion_feedback:
        parts.append(f"Coherence & Cohesion: {fb.coherence_cohesion_feedback}")
    if hasattr(fb, "lexical_resource_feedback") and fb.lexical_resource_feedback:
        parts.append(f"Lexical Resource: {fb.lexical_resource_feedback}")
    if hasattr(fb, "grammatical_range_feedback") and fb.grammatical_range_feedback:
        parts.append(f"Grammatical Range: {fb.grammatical_range_feedback}")
    if hasattr(fb, "suggestion") and fb.suggestion:
        parts.append(f"Suggestion: {fb.suggestion}")
    if hasattr(fb, "overall_score"):
        parts.append(f"Estimated score: {fb.overall_score}")
    if isinstance(fb, dict):
        for k in ["task_achievement_feedback", "coherence_cohesion_feedback", "lexical_resource_feedback", "grammatical_range_feedback", "suggestion"]:
            if fb.get(k):
                parts.append(f"{k.replace('_', ' ').title()}: {fb[k]}")
        if fb.get("overall_score") is not None:
            parts.append(f"Estimated score: {fb['overall_score']}")
    return "\n".join(parts) if parts else str(fb)


def write_essay_node(
    state: JihanState,
    *,
    writer: StreamWriter,
) -> dict:
    """
    Write the full IELTS Task 1 essay. If grading_feedback exists and passed=False,
    revise the essay based on the feedback.
    """
    grading_feedback = state.get("grading_feedback")
    previous_essay = state.get("essay", "")

    if grading_feedback and _grading_needs_revision(grading_feedback):
        writer("✏️ Processing: Revising essay based on grading feedback...")
    else:
        writer("✏️ Processing: Writing IELTS Task 1 essay...")

    model = get_text_model()
    band_score = state["band_score"]
    raw_question = state["raw_question"]
    features = state.get("extracted_features")

    features_str = features.model_dump_json(indent=2) if features and hasattr(features, "model_dump_json") else str(features or {})

    system_prompt = f"""You are an expert IELTS Writing Task 1 tutor. Write a complete essay that would score Band {band_score}.

IELTS Task 1 structure:
- Overview (2-3 sentences): Summarize main trends
- Body paragraph 1: Detail first main feature
- Body paragraph 2: Detail second main feature

Band {band_score} expectations:
- Use vocabulary and grammar appropriate for Band {band_score}
- Include relevant data and comparisons
- Write 150+ words
- Be clear and coherent"""

    if grading_feedback and _grading_needs_revision(grading_feedback):
        feedback_str = _format_grading_feedback(grading_feedback)
        system_prompt += f"\n\nREVISE the following essay based on this feedback:\n{feedback_str}\n\nPrevious essay to improve:\n{previous_essay}"

    user_content = f"""Question: {raw_question}

Extracted features:
{features_str}

Write a complete IELTS Writing Task 1 essay. Output ONLY the essay text, no explanations."""

    writer("✏️ Generating essay...")
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]
    response = model.invoke(messages)
    essay = response.content.strip() if response.content else ""

    writer("✅ Essay written successfully.")
    # Clear grading_feedback when done (indicates no pending revision)
    return {
        "essay": essay,
        "grading_feedback": GradingFeedback(
            passed=True,
            task_achievement_feedback="",
            coherence_cohesion_feedback="",
            lexical_resource_feedback="",
            grammatical_range_feedback="",
            suggestion="",
            overall_score=0.0,
        ),
    }
