"""Node 5: Grade essay against IELTS criteria. Max 3 retries."""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import StreamWriter

from config import get_text_model
from schemas.state import JihanState

MAX_GRADING_RETRIES = 3


def grade_essay_node(
    state: JihanState,
    *,
    writer: StreamWriter,
) -> dict:
    """
    Grade the essay. If it meets the band, return yes and end.
    If not, return feedback and loop back to node_4. Max 3 retries.
    """
    writer("📋 Processing: Grading essay against IELTS criteria...")

    retry_count = state.get("grading_retry_count", 0)

    if retry_count >= MAX_GRADING_RETRIES:
        writer("⏭️ Max grading retries reached. Accepting current essay.")
        return {"grading_passed": True, "grading_feedback": ""}

    model = get_text_model()
    band_score = state["band_score"]
    essay = state.get("essay", "")
    raw_question = state.get("raw_question", "")

    system_prompt = f"""You are a certified IELTS examiner. Grade this Writing Task 1 essay for Band {band_score}.

IELTS Writing Task 1 criteria:
1. Task Achievement: Does it address all requirements? Overview? Key features with data?
2. Coherence and Cohesion: Logical organization, linking words
3. Lexical Resource: Vocabulary range and accuracy for Band {band_score}
4. Grammatical Range and Accuracy: Sentence structures, grammar

Respond in EXACTLY this format (nothing else):
VERDICT: yes
OR
VERDICT: no

If no, also include:
FEEDBACK:
- [Specific errors to fix]
- [Vocabulary suggestions for Band {band_score}]
- [Score breakdown: TA/X, CC/X, LR/X, GRA/X and what to improve]"""

    user_content = f"""Question: {raw_question}

Essay to grade:
{essay}

Does this essay meet or exceed Band {band_score}?"""

    writer("📋 Evaluating essay...")
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]
    response = model.invoke(messages)
    content = (response.content or "").strip().upper()

    passed = "VERDICT: YES" in content
    feedback = ""

    if not passed:
        if "FEEDBACK:" in content:
            feedback = content.split("FEEDBACK:")[-1].strip()
        retry_count += 1
        writer(f"❌ Essay needs improvement. (Attempt {retry_count}/{MAX_GRADING_RETRIES})")
    else:
        writer("✅ Essay meets Band requirements!")

    return {
        "grading_passed": passed,
        "grading_retry_count": retry_count,
        "grading_feedback": feedback,
    }
