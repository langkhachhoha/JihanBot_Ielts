"""Tests for Jihan v2 routing and regulation loading (no live LLM calls)."""

from graph.workflow import route_after_hitl
from utils.regulations import load_regulation, regulation_path


def test_route_grade_only():
    assert route_after_hitl({"user_mode": "grade_only"}) == "grade"


def test_route_generate_with_outline():
    assert route_after_hitl({"user_mode": "generate", "user_outline": "intro\nbody"}) == "refine"


def test_route_generate_no_outline():
    assert route_after_hitl({"user_mode": "generate", "user_outline": None}) == "generate"
    assert route_after_hitl({"user_mode": "generate", "user_outline": ""}) == "generate"
    assert route_after_hitl({"user_mode": "generate", "user_outline": "   "}) == "generate"


def test_route_unknown_mode_defaults_to_grade():
    assert route_after_hitl({"user_mode": None}) == "grade"


def test_load_regulation_task1():
    text = load_regulation("task_1")
    assert "Task 1" in text or "TASK 1" in text.upper()
    assert len(text) > 500


def test_load_regulation_task2():
    text = load_regulation("task_2")
    assert "Task 2" in text or "TASK 2" in text.upper()
    assert len(text) > 500


def test_regulation_path_exists():
    for t in ("task_1", "task_2"):
        p = regulation_path(t)
        assert p.is_file(), p


def test_merge_hitl_planning_payload():
    """Simulate HITL merge fields for grade_only."""
    update = {
        "user_mode": "grade_only",
        "target_band": "7",
        "user_outline": None,
        "user_essay": "Hello world essay.",
        "essay_under_review": "Hello world essay.",
    }
    assert update["essay_under_review"] == update["user_essay"]
