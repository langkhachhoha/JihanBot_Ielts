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

    model = get_text_model(temperature=0.2).with_structured_output(GradingFeedback)
    band_score = state["band_score"]
    essay = state.get("essay", "")
    raw_question = state.get("raw_question", "")

    system_prompt = f"""You are a strict, certified IELTS examiner evaluating a Writing Task 1 essay. 
Your objective is to rigorously assess the essay and determine if it meets the exact standards of the target Band {band_score}.

### EVALUATION METHODOLOGY (4 CRITERIA) ###
Critique the essay ruthlessly based on the following:

1. Task Achievement (TA): 
- Does it have a clear overview with NO specific data/numbers? (If numbers are in the overview, penalize heavily).
- Are all key features highlighted and accurately supported with data?
- Are there clear comparisons where relevant?

2. Coherence and Cohesion (CC): 
- Is the information logically grouped into clear paragraphs?
- Are linking devices used naturally, or are they mechanical/repetitive (e.g., overusing "Firstly", "Secondly")?

3. Lexical Resource (LR): 
- Does the vocabulary demonstrate the range and precision expected at Band {band_score}? 
- Are there appropriate academic collocations for describing trends and data?

4. Grammatical Range and Accuracy (GRA): 
- Is there a sufficient mix of complex and simple sentences?
- Does the error density (grammar/punctuation) fall within the acceptable limits of Band {band_score}?

### SCORING & FEEDBACK RULES ###
- overall_score: Estimate the true band score (e.g., 5.5, 6.0, 6.5, 7.0, 7.5, 8.0) based on the 4 criteria above.
- passed: Set to `true` ONLY IF your `overall_score` is EQUAL TO OR GREATER THAN the target Band {band_score}. Otherwise, set to `false`.
- Feedback Fields: Do NOT give generic advice. You MUST quote specific flawed sentences or missing data from the essay to justify your critique. (e.g., Instead of "Improve vocabulary", write: "The phrase 'went up a lot' is too informal for Band {band_score}; use 'experienced a significant surge'.").
- suggestion: Provide a prioritized, actionable checklist of the top 3 things the student must change to hit the target Band {band_score}.

Output your evaluation strictly matching the required feedback structure."""

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
