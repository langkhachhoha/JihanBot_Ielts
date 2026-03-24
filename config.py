"""Configuration and model initialization for JihanBot v2."""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path)


def get_vision_model(temperature: float = 0.5) -> ChatOpenAI:
    """Vision model via Together API for image-based prompts (Task 1/2)."""
    return ChatOpenAI(
        model="Qwen/Qwen3-VL-8B-Instruct",
        api_key=os.getenv("TOGETHER_API_KEY"),
        base_url=os.getenv("TOGETHER_BASE_URL", "https://api.together.xyz/v1"),
        temperature=temperature,
    )


def get_openai_text_model(temperature: float = 0.7) -> ChatOpenAI:
    """
    OpenAI text model for generation, refinement, and grading (text-only paths).
    Default model id is gpt-5; override with OPENAI_TEXT_MODEL.
    """
    model = os.getenv("OPENAI_TEXT_MODEL", "gpt-5")
    return ChatOpenAI(
        model=model,
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=temperature,
    )


def get_text_model(temperature: float = 0.7) -> ChatOpenAI:
    """Alias for backward compatibility: prefer get_openai_text_model for v2."""
    return get_openai_text_model(temperature=temperature)
