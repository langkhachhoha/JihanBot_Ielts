"""Node 2: Extract chart/graph features (overview, paragraphs, data points) from image."""

import json
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import StreamWriter

from config import get_vision_model
from schemas.state import JihanState, ExtractedFeatures
from utils.image import load_image_as_base64


def extract_features_node(
    state: JihanState,
    *,
    writer: StreamWriter,
) -> dict:
    """
    Extract data features from the image. If extraction_feedback exists in state,
    correct the previous extraction based on the feedback.
    """
    extraction_feedback = state.get("extraction_feedback", "")
    extracted_features = state.get("extracted_features")

    if extraction_feedback:
        writer("🔄 Processing: Correcting extracted features based on feedback...")
    else:
        writer("📊 Processing: Extracting chart/graph features from image...")

    vision_model = get_vision_model().with_structured_output(ExtractedFeatures)
    image_path = state["image_path"]
    raw_question = state["raw_question"]
    image_url = load_image_as_base64(image_path)

    system_prompt = """You are an IELTS student carefully outlining your Writing Task 1 essay before writing the full text.
Your task is to note down raw observations, key data points, and important trends from the visual to build a solid, detailed outline. 

Do NOT write full, cohesive paragraphs. Instead, list detailed, bullet-point style observations for your overview and body paragraphs.
Make sure to capture exact numbers, percentages, labels, mid-point fluctuations, intersections, plateaus, and missing/late data points so you don't miss any nuances when writing the actual essay.

### EXAMPLE 1 (Complex Line Graph - Recycling Rates of 4 Materials 1982-2010) ###

overview:
- General upward trend for most materials, though paper fluctuated significantly.
- Paper consistently remained the most recycled material despite a late decline.
- Plastics and aluminium were introduced later in the period but showed continuous growth.

paragraph_1:
- Paper: Started as the highest at roughly 65% in 1982. 
- Experienced fluctuations but reached a peak of exactly 80% in 1994. 
- Saw a steady decline afterwards, finishing at 70% in 2010.
- Glass: Began at 50% in 1982, dropped to a low of 40% in 1990.
- Recovered and climbed consistently to end the period at 60%.

paragraph_2:
- Aluminium: No recycling data recorded until 1986 (starting at ~5%).
- Experienced a sharp exponential increase to 15% by 1994.
- Plateaued for a few years before surging again to finish at nearly 45% in 2010.
- Plastics: Data only emerged in 1990 at a mere 2%.
- Showed a slow but steady upward trajectory, ending as the lowest category at around 8% in 2010.

grouping_logic:
"I will divide the paragraphs based on the timeline of the data presence: Paragraph 1 focuses on the established materials present from the very beginning (paper and glass), while Paragraph 2 analyzes the newer materials that were introduced later in the timeline (aluminium and plastics)."

### EXAMPLE 2 (Mixed Chart - Bar Chart on Reasons for Study & Pie Chart on Employer Support by Age) ###

overview:
- Career-driven motives dominate younger age groups, whereas studying for personal interest becomes the primary reason for older groups.
- There is a clear inverse correlation between age and employer support: younger students receive the most help, while older students receive the least.

paragraph_1:
- Bar Chart (Reasons): Under 26 age group overwhelmingly studies for their career (80%), compared to just 10% for interest.
- Age 26-39 and 40-49: The gap narrows progressively. For the 40-49 demographic, career reasons drop to 50% while interest rises to 20%.
- Over 49 group: The trend reverses completely. Nearly 70% study for interest, while career motives plummet to roughly 18%.

paragraph_2:
- Pie Chart (Support): Under 26 group receives the highest level of employer support, with over 60% getting time off and help with fees.
- Support levels decline steadily across the middle age brackets, dropping to roughly 30% for the 40-49 group.
- Over 49 group receives the absolute minimum support, with only about 10% getting financial or time-off assistance from their employers.

grouping_logic:
"I will group the information by visual format and theme: Paragraph 1 will focus exclusively on the bar chart to analyze the shifting motives for studying across ages, while Paragraph 2 will analyze the pie charts to discuss the varying levels of employer support."
"""

    if extraction_feedback:
        system_prompt += f"\n\nIMPORTANT - Previous extraction had errors. Please correct based on this feedback:\n{extraction_feedback}\n\nYour previous (incorrect) extraction was:\n{json.dumps(extracted_features, indent=2) if extracted_features else 'N/A'}"

    user_content = [
        {"type": "text", "text": f"Question: {raw_question}\n\nExtract features from this IELTS Task 1 image:"},
        {"type": "image_url", "image_url": {"url": image_url}},
    ]

    writer("📊 Analyzing visual data...")
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]
    response = vision_model.invoke(messages)
    content = response.content.strip() if response.content else "{}"

    # Parse JSON (handle markdown code blocks if present)
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        data = json.loads(content)
        features = ExtractedFeatures(
            overview=data.get("overview", ""),
            paragraph_1=data.get("paragraph_1", ""),
            paragraph_2=data.get("paragraph_2", ""),
            data_points=data.get("data_points", []),
        )
    except json.JSONDecodeError:
        features = ExtractedFeatures(
            overview=content,
            paragraph_1="",
            paragraph_2="",
            data_points=[],
        )

    writer("✅ Features extracted successfully.")
    return {"extracted_features": features, "extraction_feedback": ""}
