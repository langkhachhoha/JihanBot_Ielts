"""
JihanBot - IELTS Writing Task 1 Generator
Main app for testing the pipeline with custom streaming.
"""

from pathlib import Path

from dotenv import load_dotenv

from graph.workflow import create_jihan_graph
from schemas.state import JihanState

# Load environment
load_dotenv(Path(__file__).parent / ".env")


def run_jihan_bot(image_path: str, band_score: str = "7"):
    """
    Run JihanBot pipeline with custom streaming for user feedback.

    Args:
        image_path: Path to IELTS Task 1 question image (local file)
        band_score: Target IELTS band (e.g., "6", "7", "8")
    """
    graph = create_jihan_graph()

    initial_state: JihanState = {
        "image_path": image_path,
        "band_score": band_score,
        "raw_question": "",
        "extracted_features": None,
        "extraction_feedback": None,
        "extraction_retry_count": 0,
        "essay": "",
        "grading_feedback": None,
        "grading_retry_count": 0,
    }

    config = {"configurable": {"thread_id": "jihan-1"}}

    print("=" * 60)
    print("🚀 JihanBot - IELTS Writing Task 1 Generator")
    print("=" * 60)
    print(f"Image: {image_path}")
    print(f"Target Band: {band_score}")
    print("=" * 60)

    # Stream: custom = processing messages, messages = LLM tokens
    for chunk in graph.stream(
        initial_state,
        config=config,
        stream_mode=["custom", "messages"],
    ):
        # Chunk format: (mode, data) or (namespace, mode, data)
        if isinstance(chunk, tuple):
            if len(chunk) == 3:
                _ns, mode, data = chunk
            else:
                mode, data = chunk
            if mode == "custom" and data:
                print(data)
            elif mode == "messages" and data:
                msg, _meta = data
                content = getattr(msg, "content", None) or ""
                if isinstance(content, str) and content:
                    print(content, end="", flush=True)
        elif chunk:
            print(chunk)

    # Get final state
    final_state = graph.get_state(config)
    state_values = final_state.values if hasattr(final_state, "values") else {}

    print("\n" + "=" * 60)
    print("📝 FINAL ESSAY")
    print("=" * 60)
    essay = state_values.get("essay", "")
    if essay:
        print(essay)
    else:
        print("No essay generated.")
    print("=" * 60)

    return state_values


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_ielts_task1_image> [band_score]")
        print("Example: python main.py ./sample_ielts_task1.png 7")
        sys.exit(1)

    image_path = sys.argv[1]
    band_score = sys.argv[2] if len(sys.argv) > 2 else "7"

    if not Path(image_path).exists():
        print(f"Error: Image not found: {image_path}")
        sys.exit(1)

    run_jihan_bot(image_path, band_score)
