"""State schema for JihanBot IELTS Writing v2 (Task 1 and Task 2: generate + grade)."""

from typing import Literal, Optional, TypedDict

from pydantic import BaseModel, Field


TaskType = Literal["task_1", "task_2"]
PromptKind = Literal["image", "text", "image_text"]
UserMode = Literal["generate", "grade_only"]


class GradingAndRefinementResult(BaseModel):
    """Structured grading + lightly refined essay from node_4."""

    task_criterion_feedback: str = Field(
        description="Feedback for Task Achievement (Task 1) or Task Response (Task 2)."
    )
    coherence_cohesion_feedback: str = Field(
        description="Feedback for Coherence and Cohesion."
    )
    lexical_resource_feedback: str = Field(
        description="Feedback for Lexical Resource."
    )
    grammatical_range_feedback: str = Field(
        description="Feedback for Grammatical Range and Accuracy."
    )
    score_task: float = Field(
        description="Band score for Task Achievement / Task Response (whole or half band)."
    )
    score_cc: float = Field(description="Band score for Coherence and Cohesion.")
    score_lr: float = Field(description="Band score for Lexical Resource.")
    score_gra: float = Field(description="Band score for Grammatical Range and Accuracy.")
    overall_task_band: float = Field(
        description="Task band: mean of the four criterion scores, rounded to nearest half band."
    )
    refined_essay: str = Field(
        description="Essay after light editing for clarity/accuracy/cohesion; must preserve content and stance."
    )
    revision_summary: str = Field(
        default="",
        description="Short bullet-style summary of edits applied in refined_essay.",
    )


class JihanState(TypedDict, total=False):
    """State shared across JihanBot v2 nodes."""

    # Source (set before / at ingest)
    task_type: TaskType
    prompt_kind: PromptKind
    source_image_path: Optional[str]
    source_prompt_text: str

    # HITL planning (node_1) — filled when client resumes interrupt
    user_mode: Optional[UserMode]
    target_band: str
    user_outline: Optional[str]
    user_essay: Optional[str]

    # Pipeline
    refined_brief: Optional[str]
    generated_essay: Optional[str]
    essay_under_review: str
    grading_output: Optional[GradingAndRefinementResult]

    human_review_planning: Optional[bool]
