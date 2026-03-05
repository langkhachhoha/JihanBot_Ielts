"""Node 4: Write full IELTS Writing Task 1 essay according to band score."""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import StreamWriter

from config import get_text_model
from schemas.state import JihanState, ExtractedFeatures, GradingFeedback


def _grading_needs_revision(fb) -> bool:
    """Check if grading_feedback indicates revision is needed."""
    if fb is None:
        return False
    return not (fb.passed if hasattr(fb, "passed") else (fb.get("passed", True) if isinstance(fb, dict) else True))


def _format_grading_feedback(fb) -> str:
    """Format GradingFeedback for the revision prompt."""
    if fb is None:
        return ""
    parts = []
    if hasattr(fb, "task_achievement_feedback") and fb.task_achievement_feedback:
        parts.append(f"Task Achievement: {fb.task_achievement_feedback}")
    if hasattr(fb, "coherence_cohesion_feedback") and fb.coherence_cohesion_feedback:
        parts.append(f"Coherence & Cohesion: {fb.coherence_cohesion_feedback}")
    if hasattr(fb, "lexical_resource_feedback") and fb.lexical_resource_feedback:
        parts.append(f"Lexical Resource: {fb.lexical_resource_feedback}")
    if hasattr(fb, "grammatical_range_feedback") and fb.grammatical_range_feedback:
        parts.append(f"Grammatical Range: {fb.grammatical_range_feedback}")
    if hasattr(fb, "suggestion") and fb.suggestion:
        parts.append(f"Suggestion: {fb.suggestion}")
    if hasattr(fb, "overall_score"):
        parts.append(f"Estimated score: {fb.overall_score}")
    if isinstance(fb, dict):
        for k in ["task_achievement_feedback", "coherence_cohesion_feedback", "lexical_resource_feedback", "grammatical_range_feedback", "suggestion"]:
            if fb.get(k):
                parts.append(f"{k.replace('_', ' ').title()}: {fb[k]}")
        if fb.get("overall_score") is not None:
            parts.append(f"Estimated score: {fb['overall_score']}")
    return "\n".join(parts) if parts else str(fb)

def _format_features(features) -> str:
    """Format ExtractedFeedback for the correction prompt."""
    if features is None:
        return ""
    parts = []
    if hasattr(features , "overview") and features.overview:
        parts.append(f"Overview: {features.overview}")
    if hasattr(features, "paragraph_1") and features.paragraph_1:
        parts.append(f"Paragraph 1: {features.paragraph_1}")
    if hasattr(features, "paragraph_2") and features.paragraph_2:
        parts.append(f"Paragraph 2: {features.paragraph_2}")
    if isinstance(features, dict):
        if features.get("overview"):
            parts.append(f"Overview: {features['overview']}")
        if features.get("paragraph_1"):
            parts.append(f"Paragraph 1: {features['paragraph_1']}")
        if features.get("paragraph_2"):
            parts.append(f"Paragraph 2: {features['paragraph_2']}")
    return "\n\n".join(parts) if parts else str(features)


def write_essay_node(
    state: JihanState,
    *,
    writer: StreamWriter,
) -> dict:
    """
    Write the full IELTS Task 1 essay. If grading_feedback exists and passed=False,
    revise the essay based on the feedback.
    """
    grading_feedback = state.get("grading_feedback")
    previous_essay = state.get("essay", "")

    if grading_feedback and _grading_needs_revision(grading_feedback):
        writer("✏️ Processing: Revising essay based on grading feedback...")
    else:
        writer("✏️ Processing: Writing IELTS Task 1 essay...")

    model = get_text_model()
    band_score = state["band_score"]
    raw_question = state["raw_question"]
    features = state.get("extracted_features")

    features_str = _format_features(features)

    system_prompt = f"""You are an elite IELTS former examiner and expert essay writer. Your task is to write a COMPLETE IELTS Writing Task 1 essay based on the provided data outline.

CRITICAL INSTRUCTION: You must precisely calibrate your writing to score EXACTLY a Band {band_score}. Do not overwrite or underwrite. If a Band 6.0 is requested, write like a Band 6.0 student. If an 8.5 is requested, write at a near-native academic level.

### STRICT STRUCTURAL REQUIREMENTS ###
1. Introduction (1 sentence): Paraphrase the original question/prompt accurately.
2. Overview (1-2 sentences): Summarize the macro-trends and key features. STRICTLY NO NUMBERS OR EXACT DATA in this paragraph.
3. Body Paragraph 1: Seamlessly translate the provided bullet points for the first data group into cohesive sentences.
4. Body Paragraph 2: Seamlessly translate the provided bullet points for the remaining data group into cohesive sentences.

### BAND {band_score} EXECUTION CALIBRATION ###
To perfectly mimic a Band {band_score} performance, dynamically adjust your output across the 4 marking criteria:

- Task Achievement (TA): 
  (Band 5-6: May lack clear comparisons or leave out key data. Band 7: Clear overview and good focus. Band 8+: Skillful highlighting of key differences and perfectly accurate data translation).
- Coherence and Cohesion (CC): 
  (Band 5-6: Mechanical, repetitive, or faulty linking words like "Firstly", "In addition". Band 7: Logical progression with a range of cohesive devices. Band 8+: Seamless, invisible transitions and sophisticated referencing).
- Lexical Resource (LR): 
  (Band 5-6: Basic, everyday vocabulary with some repetition or inappropriate word choices. Band 7: Uses less common vocabulary with some awareness of style. Band 8+: Precise, sophisticated collocations, and uncommon lexical items used naturally).
- Grammatical Range and Accuracy (GRA): 
  (Band 5-6: Mix of simple and complex sentences, frequent grammatical or punctuation errors. Band 7: Good control of grammar, frequent error-free sentences. Band 8+: Wide range of flexible, complex structures; the majority of sentences are error-free).

### GENERATION RULES ###
- GROUND TRUTH: You must ONLY use the data points, numbers, and trends provided in the input outline. DO NOT hallucinate, invent, or assume any information.
- LENGTH: Ensure the essay is at least 150 words.
- OUTPUT FORMAT: Output ONLY the raw text of the essay. Do not include titles, markdown formatting, greetings, or meta-commentary about the band score.
"""

    if grading_feedback and _grading_needs_revision(grading_feedback):
        feedback_str = _format_grading_feedback(grading_feedback)
        system_prompt = f"""You are an expert IELTS Writing Task 1 editor. Your task is to EDIT and REFINE an existing essay draft based on specific examiner feedback to ensure it exactly meets the standards of a Band {band_score}.

### EDITING PHILOSOPHY & CONSTRAINTS ###
- DO NOT rewrite the essay from scratch.
- PRESERVE the original essay's structure, flow, and correct sentences as much as possible.
- Make targeted, precise modifications ONLY where necessary to address the feedback and achieve the target Band {band_score}.

### TARGET BAND {band_score} CALIBRATION ###
When making your specific edits, adjust the text to reflect:
- Task Achievement: Fix any inaccurate data, missing key features, or hallucinations explicitly mentioned in the feedback.
- Coherence & Cohesion: Improve linking words or paragraph transitions ONLY if they are flagged in the feedback or fall short of the Band {band_score} level.
- Lexical Resource: Upgrade (or downgrade) specific vocabulary and collocations to match a Band {band_score} profile. Replace inappropriate word choices.
- Grammatical Range & Accuracy: Correct specific grammar or punctuation errors. Adjust sentence complexity only where needed to match Band {band_score} expectations.

### INPUTS FOR REVISION ###

EXPERT FEEDBACK:
{feedback_str}

EXISTING ESSAY DRAFT TO EDIT:
{previous_essay}

### EXECUTION RULES ###
1. Map the feedback strictly to the flawed sentences in the existing draft.
2. Apply the corrections seamlessly into the existing text without altering the surrounding correct information.
3. Ground Truth Verification: Ensure all modified data perfectly aligns with the original requirements. Do not invent new data during the editing process.
4. Output Format: Output ONLY the final, edited raw text of the essay. Do not include markdown formatting, titles, introductory phrases (e.g., "Here is the edited essay..."), or explanations of your edits.
"""

    user_content = f"""Question: {raw_question}

Extracted features:
{features_str}

Write a complete IELTS Writing Task 1 essay. Output ONLY the essay text, no explanations."""

    writer("✏️ Generating essay...")
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]
    response = model.invoke(messages)
    essay = response.content.strip() if response.content else ""

    writer("✅ Essay written successfully.")
    # Clear grading_feedback when done (indicates no pending revision)
    return {
        "essay": essay,
        "grading_feedback": GradingFeedback(
            passed=True,
            task_achievement_feedback="",
            coherence_cohesion_feedback="",
            lexical_resource_feedback="",
            grammatical_range_feedback="",
            suggestion="",
            overall_score=0.0,
        ),
    }
