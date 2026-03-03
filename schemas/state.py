"""State schema for JihanBot IELTS Writing Task 1 pipeline."""

from typing import List, Optional, TypedDict, Literal
from pydantic import BaseModel, Field



class ExtractedFeatures(BaseModel):
    """Structure for extracted IELTS Writing Task 1 features."""

    overview: str = Field(
        description="Summary of the main trends and key features."
    )
    
    paragraph_1: str = Field(
        description="Detailed analysis of the first data group."
    )
    
    paragraph_2: str = Field(
        description="Detailed analysis of the remaining data."
    )
    
    grouping_logic: str = Field(
        description="The strategy used to divide the information into two paragraphs."
    )


class ExtractedFeedback(BaseModel):
    """Feedback structure for IELTS Writing Task 1 components."""

    passed: bool = Field(
        description="Whether the extraction is correct."
    )

    overview_feedback: str = Field(
        description="Critique of the main trends and key feature identification."
    )
    
    paragraph_1_feedback: str = Field(
        description="Critique of the data analysis and accuracy in the first paragraph."
    )
    
    paragraph_2_feedback: str = Field(
        description="Critique of the data analysis and accuracy in the second paragraph."
    )


class GradingFeedback(BaseModel):
    """Comprehensive feedback and grading structure for IELTS Writing Task 1."""

    passed: bool = Field(
        description="Indicates whether the essay meets the target band score requirements."
    )
    
    task_achievement_feedback: str = Field(
        description="Evaluation of data selection, accuracy, and the clarity of the overview."
    )
    
    coherence_cohesion_feedback: str = Field(
        description="Evaluation of logical organization, paragraphing, and the use of linking devices."
    )
    
    lexical_resource_feedback: str = Field(
        description="Evaluation of vocabulary range, accuracy, and appropriate use of academic terms."
    )
    
    grammatical_range_feedback: str = Field(
        description="Evaluation of sentence structure variety, grammatical accuracy, and punctuation."
    )

    suggestion: str = Field(
        description="Actionable recommendations and specific steps to adapt the essay to the target band score."
    )

    overall_score: float = Field(
        description="The final estimated overall band score (e.g., 6.0, 6.5, 7.0)."
    )


class JihanState(TypedDict):
    """State shared across all JihanBot nodes."""

    # Input
    image_path: str
    band_score: str

    # Node 1: Extract question
    raw_question: str

    # Node 2: Extract features
    extracted_features: ExtractedFeatures
    extraction_feedback: ExtractedFeedback # Feedback from node_3 when verification fails

    # Node 3: Verify extraction
    extraction_retry_count: int

    # Node 4: Write essay
    essay: str
    grading_feedback: GradingFeedback # Feedback from node_5 when grading fails

    # Node 5: Grade essay
    grading_retry_count: int
