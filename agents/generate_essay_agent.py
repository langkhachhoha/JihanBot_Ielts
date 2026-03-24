"""node_3: generate full essay with regulation-injected system prompt; VLM if image."""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import StreamWriter

from config import get_openai_text_model, get_vision_model
from schemas.state import JihanState
from utils.image import load_image_as_base64
from utils.regulations import load_regulation


def _task_label(task_type: str) -> str:
    return "Task 1" if task_type == "task_1" else "Task 2"


def generate_essay_node(
    state: JihanState,
    *,
    writer: StreamWriter,
) -> dict:
    """Generate essay; use vision model when prompt uses an image."""
    writer("✏️ Generating essay...")

    task_type = state.get("task_type", "task_1")
    band = state.get("target_band", "7")
    regulation = load_regulation(task_type)
    prompt_kind = state.get("prompt_kind", "text")
    source_text = (state.get("source_prompt_text") or "").strip()
    brief = (state.get("refined_brief") or "").strip()
    outline = (state.get("user_outline") or "").strip()
    plan_block = brief if brief else outline

    system_prompt = f"""You are an expert IELTS Writing instructor and writer.

The learner targets approximately Band {band} for IELTS Writing {_task_label(task_type)}.

### OFFICIAL-STYLE REGULATION (follow for level and criteria)
{regulation}

### YOUR JOB
Write a complete exam-style response appropriate for {_task_label(task_type)} at about Band {band}.
- Meet minimum length expectations (Task 1: at least 150 words; Task 2: at least 250 words).
- Output **only** the essay text — no titles like "Essay", no band commentary, no markdown.
- Ground content in the task: do not invent data for charts you cannot see; if an image is provided, use it faithfully."""

    user_text = f"""Task instructions / question (text):
{source_text or "(See image for full task.)"}

Generation plan / brief:
{plan_block or "(Develop a strong response consistent with the task.)"}

Write the full essay now."""

    uses_image = prompt_kind in ("image", "image_text") and state.get("source_image_path")

    if uses_image:
        model = get_vision_model(temperature=0.6)
        image_url = load_image_as_base64(state["source_image_path"])
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=[
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ]
            ),
        ]
    else:
        model = get_openai_text_model(temperature=0.7)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_text),
        ]

    response = model.invoke(messages)
    raw = response.content
    if isinstance(raw, list):
        parts = []
        for block in raw:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            else:
                parts.append(str(block))
        essay = "".join(parts).strip()
    else:
        essay = (raw or "").strip()

    writer("✅ Essay generated.")
    return {
        "generated_essay": essay,
        "essay_under_review": essay,
    }
