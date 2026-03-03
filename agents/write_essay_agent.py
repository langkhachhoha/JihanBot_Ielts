"""Node 4: Write full IELTS Writing Task 1 essay according to band score."""

import json
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import StreamWriter

from config import get_text_model
from schemas.state import JihanState


def write_essay_node(
    state: JihanState,
    *,
    writer: StreamWriter,
) -> dict:
    """
    Write the full IELTS Task 1 essay. If grading_feedback exists,
    revise the essay based on the feedback.
    """
    grading_feedback = state.get("grading_feedback", "")
    previous_essay = state.get("essay", "")

    if grading_feedback:
        writer("✏️ Processing: Revising essay based on grading feedback...")
    else:
        writer("✏️ Processing: Writing IELTS Task 1 essay...")

    model = get_text_model()
    band_score = state["band_score"]
    raw_question = state["raw_question"]
    features = state.get("extracted_features") or {}

    features_str = json.dumps(features, indent=2)

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

    if grading_feedback:
        system_prompt += f"\n\nREVISE the following essay based on this feedback:\n{grading_feedback}\n\nPrevious essay to improve:\n{previous_essay}"

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
    return {"essay": essay, "grading_feedback": ""}
