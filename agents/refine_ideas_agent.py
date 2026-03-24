"""node_2: refine user outline into a clearer generation brief (text LLM)."""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import StreamWriter

from config import get_openai_text_model
from schemas.state import JihanState


def refine_ideas_node(
    state: JihanState,
    *,
    writer: StreamWriter,
) -> dict:
    """Turn user outline + task context into a structured brief for essay generation."""
    writer("🔧 Refining user outline into a generation brief...")

    model = get_openai_text_model(temperature=0.5)
    task_type = state.get("task_type", "task_1")
    band = state.get("target_band", "7")
    outline = (state.get("user_outline") or "").strip()
    prompt_text = (state.get("source_prompt_text") or "").strip()

    task_label = "IELTS Writing Task 1 (report/letter)" if task_type == "task_1" else "IELTS Writing Task 2 (essay)"

    system = f"""You are an IELTS preparation coach. The learner will write {task_label} at about Band {band}.
They provided a rough plan/outline. Produce a concise **generation brief** the writer can follow.

Rules:
- Keep the learner's intended ideas and stance; do not invent unrelated content.
- Output clear bullets: suggested structure, key points per paragraph, and any must-include comparisons or arguments implied by the exam task.
- If the task prompt text is empty and only an image will be used later, still improve the outline logically for a typical {task_label} task.
- Output plain text only, no markdown links."""

    user = f"""Exam task text (may be empty if image-only):\n{prompt_text or "(none)"}

Learner outline:
{outline}

Write the generation brief."""

    messages = [SystemMessage(content=system), HumanMessage(content=user)]
    response = model.invoke(messages)
    brief = (response.content or "").strip()
    writer("✅ Brief ready.")
    return {"refined_brief": brief}
