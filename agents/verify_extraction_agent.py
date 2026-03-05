"""Node 3: Verify extracted features against the image. Max 3 retries."""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import StreamWriter

from config import get_vision_model
from schemas.state import JihanState, ExtractedFeedback, ExtractedFeatures
from utils.image import load_image_as_base64


MAX_EXTRACTION_RETRIES = 3

def _format_features(features) -> str:
    """Format ExtractedFeedback for the correction prompt."""
    if features is None:
        return ""
    parts = []
    if hasattr(features , "overview") and features.overview:
        parts.append(f"Overview: {features.overview}")
    if hasattr(features, "paragraph_1") and features.paragraph_1:
        parts.append(f"Paragraph 1: {features.paragraph_1}")
    if hasattr(features, "paragraph_2") and features.paragraph_2:
        parts.append(f"Paragraph 2: {features.paragraph_2}")
    if isinstance(features, dict):
        if features.get("overview"):
            parts.append(f"Overview: {features['overview']}")
        if features.get("paragraph_1"):
            parts.append(f"Paragraph 1: {features['paragraph_1']}")
        if features.get("paragraph_2"):
            parts.append(f"Paragraph 2: {features['paragraph_2']}")
    return "\n\n".join(parts) if parts else str(features)


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

    extracted_str = _format_features(extracted)

    system_prompt = """You are a meticulous IELTS examiner verifying data extraction accuracy against the provided Task 1 visual.

### VERIFICATION METHODOLOGY & TOLERANCE LEVEL ###
Evaluate the extraction using these criteria. Note the difference between FATAL errors and MINOR errors.

1. OVERVIEW VERIFICATION:
- Macro-trends: Must accurately capture the overall trajectories.
- NO DATA RULE: The overview MUST NOT contain specific numbers. 
- FATAL ERROR (passed=False): Including specific data in the overview, or completely misidentifying the main trend.

2. PARAGRAPH 1 & 2 VERIFICATION (Data & Features):
- Visual Approximation Tolerance: Accept reasonable approximations for data points that are visually ambiguous (e.g., accepting 42, 45, or "just under 50" for a point between 40 and 50). 
- FATAL ERROR (passed=False): Misidentifying trends (saying "increased" instead of "decreased"), mixing up categories (e.g., confusing Paper with Glass), hallucinating non-existent data, or missing crucial milestones like intersections and peaks.
- MINOR ERROR (passed=True): Slight data approximations, minor phrasing issues, or missing a very small, insignificant data point that does not skew the overall analysis.

3. GROUPING LOGIC VERIFICATION:
- The rationale for dividing data must be logical.

### FEEDBACK RULES ###
- Set `passed=True` if the extraction is fundamentally accurate and captures all key features correctly, EVEN IF there are minor, acceptable approximations. You MUST still use the feedback fields to suggest refinements for these minor issues.
- Set `passed=False` ONLY IF there is a FATAL ERROR (hallucinations, missed key intersections, wrong trends, or data in the overview).
- Be EXTREMELY SPECIFIC in your feedback (e.g., "Change 40% to approximately 45%").

### EXAMPLES ###

**Example 1: Acceptable Extraction (passed=True)**
- Student extracted: "Paper reached a peak of 82% in 1994."
- Actual visual: The peak looks like it could be 80%, 81%, or 82%.
- Your Feedback: `passed=True`. "Para 1 Feedback: The peak for paper in 1994 is acceptable at 82%, though it might be closer to exactly 80%. No major changes needed."

**Example 2: Fatal Error (passed=False)**
- Student extracted: "Glass consumption steadily increased from 1982 to 1990."
- Actual visual: Glass consumption actually dropped in that period.
- Your Feedback: `passed=False`. "Para 1 Feedback: FATAL ERROR. Glass consumption did NOT increase; it dropped from 50% in 1982 to 40% in 1990. Please correct the trend direction."
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
                content = [
                        {
                            "type": "text", 
                            "text": f"""Question: {raw_question}\n\nPlease critically evaluate the following extracted features against the attached image. 
                            \nRemember your role: Apply the 'Visual Approximation Tolerance' for acceptable minor deviations, but strictly flag any FATAL ERRORS 
                            (wrong trends, missed milestones, or numbers in the overview).\n\nExtracted features to verify:\n{extracted_str}"""
                        },
                        {
                            "type": "image_url", 
                            "image_url": {"url": image_url}
                        },
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
