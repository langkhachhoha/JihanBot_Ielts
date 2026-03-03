"""Node 3: Verify extracted features against the image. Max 3 retries."""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import StreamWriter

from config import get_vision_model
from schemas.state import JihanState
from utils.image import load_image_as_base64

MAX_EXTRACTION_RETRIES = 3


def verify_extraction_node(
    state: JihanState,
    *,
    writer: StreamWriter,
) -> dict:
    """
    Compare extracted features with the image. Return yes/feedback.
    After 3 retries, auto-proceed to node_4.
    """
    writer("🔍 Processing: Verifying extracted data against image...")

    retry_count = state.get("extraction_retry_count", 0)

    if retry_count >= MAX_EXTRACTION_RETRIES:
        writer("⏭️ Max retries reached. Proceeding to essay writing...")
        return {"extraction_verified": True, "verification_feedback": ""}

    vision_model = get_vision_model()
    image_path = state["image_path"]
    image_url = load_image_as_base64(image_path)
    extracted = state.get("extracted_features") or {}
    raw_question = state.get("raw_question", "")

    import json
    extracted_str = json.dumps(extracted, indent=2)

    system_prompt = """You are a strict IELTS examiner verifying data extraction accuracy.
Compare the extracted features with the image. Check:
1. All numbers, percentages, and labels are correct
2. No data is missing or fabricated
3. Overview accurately summarizes the main trends
4. Paragraph descriptions match the visual

Respond in EXACTLY this format (nothing else):
VERDICT: yes
OR
VERDICT: no
FEEDBACK: [Detailed list of specific errors to fix - which numbers are wrong, what's missing, etc.]"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=[
                {"type": "text", "text": f"Question: {raw_question}\n\nExtracted features to verify:\n{extracted_str}"},
                {"type": "image_url", "image_url": {"url": image_url}},
            ]
        ),
    ]

    writer("🔍 Comparing data with image...")
    print("extracted_str", extracted_str)
    response = vision_model.invoke(messages)
    content = (response.content or "").strip().upper()

    passed = "VERDICT: YES" in content
    feedback = ""

    if not passed:
        if "FEEDBACK:" in content:
            feedback = content.split("FEEDBACK:")[-1].strip()
        retry_count += 1
        writer(f"❌ Verification failed. Feedback recorded. (Attempt {retry_count}/{MAX_EXTRACTION_RETRIES})")
    else:
        writer("✅ Data verified successfully.")

    return {
        "extraction_verified": passed,
        "extraction_retry_count": retry_count,
        "verification_feedback": feedback,
        "extraction_feedback": feedback if not passed else "",
    }
