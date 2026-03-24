"""Ingest and validate source prompt (image path and/or text) for v2 pipeline."""

from pathlib import Path

from langgraph.types import StreamWriter

from schemas.state import JihanState, PromptKind


def _normalize_prompt_kind(state: JihanState) -> PromptKind:
    kind = state.get("prompt_kind")
    if kind in ("image", "text", "image_text"):
        return kind
    img = state.get("source_image_path")
    text = (state.get("source_prompt_text") or "").strip()
    if img and text:
        return "image_text"
    if img:
        return "image"
    return "text"


def ingest_source_node(
    state: JihanState,
    *,
    writer: StreamWriter,
) -> dict:
    """Validate inputs; normalize prompt_kind. Full visual understanding happens in generate when needed."""
    writer("📥 Ingesting task source...")

    task_type = state.get("task_type")
    if task_type not in ("task_1", "task_2"):
        raise ValueError("task_type must be 'task_1' or 'task_2'")

    prompt_kind = _normalize_prompt_kind(state)
    img_path = state.get("source_image_path")
    text = state.get("source_prompt_text") or ""

    if prompt_kind in ("image", "image_text"):
        if not img_path:
            raise ValueError("source_image_path required when using image prompt")
        if not Path(img_path).is_file():
            raise FileNotFoundError(f"Image not found: {img_path}")

    if prompt_kind in ("text", "image_text") and not text.strip():
        writer("⚠️ No text prompt provided; generation will rely on image only where applicable.")

    writer(f"✅ Ingest OK — task={task_type}, prompt_kind={prompt_kind}")
    return {"prompt_kind": prompt_kind}
