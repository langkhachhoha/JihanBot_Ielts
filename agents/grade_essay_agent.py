"""Node 5: Grade essay against IELTS criteria. Max 3 retries."""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import StreamWriter

from config import get_text_model
from schemas.state import JihanState, GradingFeedback

MAX_GRADING_RETRIES = 3


def grade_essay_node(
    state: JihanState,
    *,
    writer: StreamWriter,
) -> dict:
    """
    Grade the essay using structured GradingFeedback.
    If it meets the band, return passed=True and end.
    If not, return passed=False with detailed feedback; loop back to write_essay. Max 3 retries.
    """
    writer("📋 Processing: Grading essay against IELTS criteria...")

    retry_count = state.get("grading_retry_count", 0)

    if retry_count >= MAX_GRADING_RETRIES:
        writer("⏭️ Max grading retries reached. Accepting current essay.")
        return {
            "grading_retry_count": retry_count,
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

    model = get_text_model().with_structured_output(GradingFeedback)
    band_score = state["band_score"]
    essay = state.get("essay", "")
    raw_question = state.get("raw_question", "")

    system_prompt = f"""You are a certified IELTS examiner. Grade this Writing Task 1 essay for Band {band_score}.

IELTS Writing Task 1 criteria:
1. Task Achievement: Does it address all requirements? Overview? Key features with data?
2. Coherence and Cohesion: Logical organization, paragraphing, linking devices
3. Lexical Resource: Vocabulary range and accuracy for Band {band_score}
4. Grammatical Range and Accuracy: Sentence structures, grammar

Fill in the structured feedback:
- passed: True only if the essay meets or exceeds Band {band_score}
- task_achievement_feedback: Evaluation of data selection, overview, key features
- coherence_cohesion_feedback: Evaluation of organization and linking
- lexical_resource_feedback: Evaluation of vocabulary for the target band
- grammatical_range_feedback: Evaluation of grammar and sentence variety
- suggestion: Actionable steps to improve if not meeting band
- overall_score: Your estimated band score (e.g., 6.0, 6.5, 7.0)"""

    user_content = f"""Question: {raw_question}

Essay to grade:
{essay}

Does this essay meet or exceed Band {band_score}? Provide structured feedback."""

    writer("📋 Evaluating essay...")
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]
    feedback = model.invoke(messages)

    if not isinstance(feedback, GradingFeedback):
        feedback = GradingFeedback(
            passed=False,
            task_achievement_feedback=str(feedback),
            coherence_cohesion_feedback="",
            lexical_resource_feedback="",
            grammatical_range_feedback="",
            suggestion="",
            overall_score=0.0,
        )

    if not feedback.passed:
        retry_count += 1
        writer(f"❌ Essay needs improvement. (Attempt {retry_count}/{MAX_GRADING_RETRIES})")
    else:
        writer("✅ Essay meets Band requirements!")

    return {
        "grading_retry_count": retry_count,
        "grading_feedback": feedback,
    }
