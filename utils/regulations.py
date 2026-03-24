"""Load IELTS Writing regulation markdown for Task 1 / Task 2."""

from pathlib import Path
from typing import Literal

from schemas.state import TaskType

_REG_DIR = Path(__file__).resolve().parent.parent / "regulations"
_FILE_NAMES: dict[TaskType, str] = {
    "task_1": "ielts_writing_task_1_regulation.md",
    "task_2": "ielts_writing_task_2_regulation.md",
}


def load_regulation(task_type: TaskType) -> str:
    """Return full regulation markdown text for the given task type."""
    name = _FILE_NAMES.get(task_type)
    if not name:
        raise ValueError(f"Unknown task_type: {task_type}")
    path = _REG_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"Regulation file not found: {path}")
    return path.read_text(encoding="utf-8")


def regulation_path(task_type: TaskType) -> Path:
    """Absolute path to the regulation file (for tests)."""
    return _REG_DIR / _FILE_NAMES[task_type]
