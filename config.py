"""Configuration and model initialization for JihanBot."""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load .env from Jihan folder; override=True để ưu tiên giá trị trong .env, bỏ qua biến môi trường hệ thống
_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path)


def get_vision_model(temperature: float = 0.5) -> ChatOpenAI:
    """Get vision model via Together API for image understanding.
    Uses Qwen3-VL-8B (serverless); alternatives: Qwen/Qwen3-VL-32B-Instruct,
    meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"""
    return ChatOpenAI(
        model="Qwen/Qwen3-VL-8B-Instruct",
        api_key=os.getenv("TOGETHER_API_KEY"),
        base_url=os.getenv("TOGETHER_BASE_URL", "https://api.together.xyz/v1"),
        temperature=temperature,
    )


def get_text_model(temperature: float = 0.7) -> ChatOpenAI:
    """Get text model for essay generation.
    Default: Together (Llama 4 Maverick). Set USE_TOGETHER_FOR_TEXT=false to use OpenAI gpt-4o."""
    if os.getenv("USE_TOGETHER_FOR_TEXT", "true").lower() != "false":
        return ChatOpenAI(
            model=os.getenv("TOGETHER_TEXT_MODEL", "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"),
            api_key=os.getenv("TOGETHER_API_KEY"),
            base_url=os.getenv("TOGETHER_BASE_URL", "https://api.together.xyz/v1"),
            temperature=temperature,
        )
    return ChatOpenAI(
        model="gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=temperature,
    )
