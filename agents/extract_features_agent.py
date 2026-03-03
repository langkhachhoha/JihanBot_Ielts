"""Node 2: Extract chart/graph features (overview, paragraphs, data points) from image."""

import json
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import StreamWriter

from config import get_vision_model
from schemas.state import JihanState, ExtractedFeatures
from utils.image import load_image_as_base64


def extract_features_node(
    state: JihanState,
    *,
    writer: StreamWriter,
) -> dict:
    """
    Extract data features from the image. If extraction_feedback exists in state,
    correct the previous extraction based on the feedback.
    """
    extraction_feedback = state.get("extraction_feedback", "")
    extracted_features = state.get("extracted_features")

    if extraction_feedback:
        writer("🔄 Processing: Correcting extracted features based on feedback...")
    else:
        writer("📊 Processing: Extracting chart/graph features from image...")

    vision_model = get_vision_model()
    image_path = state["image_path"]
    raw_question = state["raw_question"]
    image_url = load_image_as_base64(image_path)

    system_prompt = """You are an expert at analyzing IELTS Writing Task 1 visuals (charts, graphs, tables).
Extract the key features in the following JSON structure:
{
  "overview": "2-3 sentence summary of main trends/patterns",
  "paragraph_1": "Detailed description of first main feature/category with specific data",
  "paragraph_2": "Detailed description of second main feature/category with specific data",
  "data_points": [{"label": "Category/Year", "value": "number or percentage", "unit": "optional"}]
}
Ensure all numbers, percentages, and labels match the image EXACTLY.
Output ONLY valid JSON, no markdown or extra text."""

    if extraction_feedback:
        system_prompt += f"\n\nIMPORTANT - Previous extraction had errors. Please correct based on this feedback:\n{extraction_feedback}\n\nYour previous (incorrect) extraction was:\n{json.dumps(extracted_features, indent=2) if extracted_features else 'N/A'}"

    user_content = [
        {"type": "text", "text": f"Question: {raw_question}\n\nExtract features from this IELTS Task 1 image:"},
        {"type": "image_url", "image_url": {"url": image_url}},
    ]

    writer("📊 Analyzing visual data...")
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]
    response = vision_model.invoke(messages)
    content = response.content.strip() if response.content else "{}"

    # Parse JSON (handle markdown code blocks if present)
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        data = json.loads(content)
        features = ExtractedFeatures(
            overview=data.get("overview", ""),
            paragraph_1=data.get("paragraph_1", ""),
            paragraph_2=data.get("paragraph_2", ""),
            data_points=data.get("data_points", []),
        )
    except json.JSONDecodeError:
        features = ExtractedFeatures(
            overview=content,
            paragraph_1="",
            paragraph_2="",
            data_points=[],
        )

    writer("✅ Features extracted successfully.")
    return {"extracted_features": features, "extraction_feedback": ""}
