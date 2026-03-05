"""Node 3: Verify extracted features against the image. Max 3 retries."""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import StreamWriter

from config import get_vision_model
from schemas.state import JihanState, ExtractedFeedback, ExtractedFeatures
from utils.image import load_image_as_base64

MAX_EXTRACTION_RETRIES = 3


def verify_extraction_node(
    state: JihanState,
    *,
    writer: StreamWriter,
) -> dict:
    """
    Compare extracted features with the image. Return ExtractedFeedback with passed=True/False.
    After 3 retries, auto-proceed (return passed=True).
    """
    writer("🔍 Processing: Verifying extracted data against image...")

    retry_count = state.get("extraction_retry_count", 0)

    if retry_count >= MAX_EXTRACTION_RETRIES:
        writer("⏭️ Max retries reached. Proceeding to essay writing...")
        return {
            "extraction_retry_count": retry_count,
            "extraction_feedback": ExtractedFeedback(passed=True, overview_feedback="", paragraph_1_feedback="", paragraph_2_feedback=""),
        }

    vision_model = get_vision_model().with_structured_output(ExtractedFeedback)
    image_path = state["image_path"]
    image_url = load_image_as_base64(image_path)
    extracted = state.get("extracted_features")
    raw_question = state.get("raw_question", "")

    extracted_str = extracted.model_dump_json(indent=2) if extracted and hasattr(extracted, "model_dump_json") else str(extracted or {})

    system_prompt = """You are a strict IELTS examiner verifying data extraction accuracy.
Compare the extracted features with the image. Check:
1. All numbers, percentages, and labels are correct
2. No data is missing or fabricated
3. Overview accurately summarizes the main trends
4. Paragraph descriptions match the visual

Provide structured feedback: set passed=True only if everything is correct. If any errors exist, set passed=False and fill in the relevant feedback fields (overview_feedback, paragraph_1_feedback, paragraph_2_feedback) with specific, actionable corrections - which numbers are wrong, what's missing, etc."""

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
    feedback = vision_model.invoke(messages)

    if not isinstance(feedback, ExtractedFeedback):
        feedback = ExtractedFeedback(
            passed=False,
            overview_feedback=str(feedback),
            paragraph_1_feedback="",
            paragraph_2_feedback="",
        )

    if not feedback.passed:
        retry_count += 1
        writer(f"❌ Verification failed. Feedback recorded. (Attempt {retry_count}/{MAX_EXTRACTION_RETRIES})")
    else:
        writer("✅ Data verified successfully.")

    return {
        "extraction_retry_count": retry_count,
        "extraction_feedback": feedback,
    }
