"""Node 1: Extract raw question text from IELTS Writing Task 1 image."""

from langchain_core.messages import HumanMessage
from langgraph.types import StreamWriter

from config import get_vision_model
from schemas.state import JihanState
from utils.image import load_image_as_base64


def extract_question_node(
    state: JihanState,
    *,
    writer: StreamWriter,
) -> dict:
    """Extract the question/prompt from the IELTS Task 1 image as raw text."""
    writer("📖 Processing: Extracting question from image...")

    vision_model = get_vision_model()
    image_path = state["image_path"]
    image_url = load_image_as_base64(image_path)

    messages = [
        HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": """You are an expert at reading IELTS Writing Task 1 exam questions.
Extract and transcribe the complete question/prompt from this image exactly as it appears.
Include all instructions, charts, graphs, or tables descriptions that are part of the question.
Output ONLY the raw extracted text, nothing else.""",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                },
            ]
        )
    ]

    writer("📖 Analyzing image content...")
    response = vision_model.invoke(messages)
    raw_question = response.content.strip() if response.content else ""

    writer("✅ Question extracted successfully.")
    return {"raw_question": raw_question}
