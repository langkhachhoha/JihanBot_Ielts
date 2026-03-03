"""State schema for JihanBot IELTS Writing Task 1 pipeline."""

from typing import List, Optional, TypedDict


class ExtractedFeatures(TypedDict):
    """Structure for extracted chart/graph features."""

    overview: str
    paragraph_1: str
    paragraph_2: str
    data_points: List[dict]


class JihanState(TypedDict):
    """State shared across all JihanBot nodes."""

    # Input
    image_path: str
    band_score: str

    # Node 1: Extract question
    raw_question: str

    # Node 2: Extract features
    extracted_features: Optional[ExtractedFeatures]
    extraction_feedback: str  # Feedback from node_3 when verification fails

    # Node 3: Verify extraction
    extraction_verified: bool
    extraction_retry_count: int
    verification_feedback: str

    # Node 4: Write essay
    essay: str
    grading_feedback: str  # Feedback from node_5 when grading fails

    # Node 5: Grade essay
    grading_passed: bool
    grading_retry_count: int
