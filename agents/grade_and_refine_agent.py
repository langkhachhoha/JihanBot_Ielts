"""node_4: grade against regulations and return feedback, scores, and lightly refined essay."""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import StreamWriter

from config import get_openai_text_model
from schemas.state import GradingAndRefinementResult, JihanState
from utils.regulations import load_regulation


def _task_criterion_name(task_type: str) -> str:
    return "Task Achievement" if task_type == "task_1" else "Task Response"


def grade_and_refine_node(
    state: JihanState,
    *,
    writer: StreamWriter,
) -> dict:
    """Produce structured grading + refined essay; preserve original meaning and stance."""
    writer("📋 Grading and light refinement...")

    task_type = state.get("task_type", "task_1")
    band = state.get("target_band", "7")
    regulation = load_regulation(task_type)

    essay = (
        state.get("essay_under_review")
        or state.get("generated_essay")
        or state.get("user_essay")
        or ""
    ).strip()
    if not essay:
        writer("⚠️ No essay text to grade.")
        empty = GradingAndRefinementResult(
            task_criterion_feedback="No essay submitted.",
            coherence_cohesion_feedback="",
            lexical_resource_feedback="",
            grammatical_range_feedback="",
            score_task=0.0,
            score_cc=0.0,
            score_lr=0.0,
            score_gra=0.0,
            overall_task_band=0.0,
            refined_essay="",
            revision_summary="",
        )
        return {"grading_output": empty}

    prompt_text = (state.get("source_prompt_text") or "").strip()
    tc_name = _task_criterion_name(task_type)

    system_prompt = f"""You are a certified IELTS Writing examiner assistant.

### REGULATION (apply when scoring)
{regulation}

### TARGET
The learner aims for about Band {band}. Score the script on four criteria using **whole or half bands** per criterion (e.g. 6.0, 6.5).
Compute **overall_task_band** as the mean of the four criterion scores, rounded to the **nearest half band** (multiply by 2, round, divide by 2).

### REFINED ESSAY RULES
- Produce **refined_essay**: fix clarity, grammar, cohesion, and lexical slips **only** where needed.
- **Do not** rewrite from scratch, change the writer's position, or replace the argument with a different one.
- Preserve factual claims and examples; do not invent new data for Task 1.

### OUTPUT
Return structured fields matching the schema. task_criterion_feedback covers **{tc_name}**."""

    user_content = f"""Task / question text:
{prompt_text or "(If task was image-only, infer from essay context.)"}

Essay to assess:
{essay}

Return JSON with all required fields including refined_essay and revision_summary."""

    model = get_openai_text_model(temperature=0.2).with_structured_output(GradingAndRefinementResult)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]
    result = model.invoke(messages)
    if not isinstance(result, GradingAndRefinementResult):
        result = GradingAndRefinementResult.model_validate(result)

    writer("✅ Grading complete.")
    return {"grading_output": result}
