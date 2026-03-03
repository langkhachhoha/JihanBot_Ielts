"""Utility for loading images for vision models."""

import base64
from pathlib import Path


def load_image_as_base64(image_path: str) -> str:
    """
    Load image from file path and return as base64 data URL.
    Compatible with LangChain vision models.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with open(path, "rb") as f:
        image_data = f.read()

    base64_str = base64.b64encode(image_data).decode("utf-8")

    # Detect MIME type from extension
    suffix = path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    mime_type = mime_map.get(suffix, "image/jpeg")

    return f"data:{mime_type};base64,{base64_str}"
