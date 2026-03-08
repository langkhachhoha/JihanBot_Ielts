"""Node: Extract learnable language units from the final essay (vocabulary, collocations, structures, patterns)."""

import json
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import StreamWriter

from config import get_gpt4o_model
from schemas.state import (
    JihanState,
    ExtractedLanguageItem,
    LanguageExtractionResult,
)

DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "language_taxonomy.json"


def _load_taxonomy(path: str | Path) -> dict | None:
    """Load taxonomy JSON from path. Returns None if file not found or invalid."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _format_taxonomy_for_prompt(taxonomy: dict) -> str:
    """Format categories and subcategories for the LLM prompt."""
    lines = []
    categories = taxonomy.get("categories", {})
    for cat_name, cat_data in categories.items():
        if isinstance(cat_data, dict):
            desc = cat_data.get("description", "")
            subs = cat_data.get("subcategories", [])
            sub_str = ", ".join(subs)
            lines.append(f"- {cat_name}: {desc}")
            lines.append(f"  Subcategories: {sub_str}")
        else:
            lines.append(f"- {cat_name}: {cat_data}")
    return "\n".join(lines)


def extract_language_units_node(
    state: JihanState,
    *,
    writer: StreamWriter,
) -> dict:
    """
    Extract learnable language units (vocabulary, collocations, sentence structures,
    expression patterns) from the final essay. Uses taxonomy for fixed categories
    and controlled subcategory extension. Output requires human-in-the-loop approval.
    """
    writer("📚 Processing: Extracting language units from final essay...")

    essay = state.get("essay", "")
    database_path = state.get("database_path") or str(DEFAULT_TAXONOMY_PATH)

    if not essay:
        writer("⚠️ No essay in state. Skipping language extraction.")
        return {
            "final_generated_essay": "",
            "proposed_language_items": [],
        }

    taxonomy = _load_taxonomy(database_path)
    if not taxonomy:
        writer(f"⚠️ Taxonomy not found at {database_path}. Skipping extraction.")
        return {
            "final_generated_essay": essay,
            "proposed_language_items": [],
        }

    taxonomy_str = _format_taxonomy_for_prompt(taxonomy)

    model = get_gpt4o_model(temperature=0.3).with_structured_output(LanguageExtractionResult)

    system_prompt = f"""
You are an expert IELTS Writing Task 1 tutor, examiner, and linguistic annotator.

Your task is to extract the most useful learnable language units from a final IELTS Writing Task 1 essay.
The goal is not to extract random phrases, but to identify language that a learner can realistically study, reuse, and adapt in future Task 1 responses.

You must focus only on language that is valuable for IELTS Writing Task 1, especially:
- topic-specific vocabulary for describing charts, graphs, tables, processes, or maps
- strong collocations commonly used in Task 1
- reusable sentence structures and reporting patterns
- useful expression patterns for overview, comparison, trend description, and quantity reporting

### TAXONOMY (YOU MUST FOLLOW THIS) ###
{taxonomy_str}

### CORE OBJECTIVE ###
Extract language items that are:
1. clearly useful for IELTS Writing Task 1
2. reusable in other Task 1 essays
3. grounded in the essay itself
4. classified consistently using the given taxonomy

### STRICT RULES ###
1. CATEGORY
- "category" MUST be exactly one of the taxonomy category names.
- DO NOT create a new category under any circumstance.

2. SUBCATEGORY
- First, try to match an existing subcategory under the selected category.
- You may create a NEW subcategory only if it is truly necessary.
- A new subcategory is allowed only when:
  - no existing subcategory fits well enough
  - it is clearly distinct in meaning from all existing subcategories
  - it logically belongs to the selected category
  - it is short, precise, and written in snake_case
- If a new subcategory is only slightly different from an existing one, you MUST reuse the existing one instead.
- When in doubt, prefer the existing subcategory.

3. STRUCTURE
- "structure" must be written in a clean, learner-friendly IELTS study format.
- It should look like a reusable template, not just a copied sentence.
- Use placeholders such as:
  - [sth]
  - [sb]
  - [X]
  - [Y]
  - [the figure]
  - [the proportion of ...]
  - [the number of ...]
  - [from X to Y]
  - [over the period]
- The structure should be short, clear, and easy for a learner to memorise.
- Prefer generalisable templates such as:
  - [the figure] increased significantly over the period
  - [X] was higher than [Y]
  - There was a sharp increase in [sth]
  - [X] accounted for the largest proportion
- Do NOT write overly abstract labels.
- Do NOT make the structure too long unless the full pattern is genuinely worth learning.

4. EXAMPLE
- "example" must come directly from the essay.
- It should be quoted verbatim or as a short exact excerpt from the essay.
- Keep it short but meaningful.
- The example must clearly demonstrate the extracted structure in context.

5. EXTRACTION QUALITY
- Extract only high-value items.
- Do NOT extract trivial or generic language unless it is clearly useful in Task 1.
- Do NOT extract duplicate items.
- If two items are very similar, keep the stronger or more reusable one.
- Prioritise items that help the learner write more naturally, accurately, and academically.

6. TASK 1 PRIORITY
Prioritise language related to:
- increases, decreases, fluctuations, stability, peaks, lows
- comparisons between categories or time points
- percentages, proportions, quantities, rankings
- overview sentences
- data introduction and reporting
- formal report-style expressions

### WHAT GOOD OUTPUT LOOKS LIKE ###
Good structures:
- [the figure] rose sharply in [year]
- [X] was considerably higher than [Y]
- There was a slight decline in [sth]
- [X] remained relatively stable throughout the period
- Overall, [X] showed an upward trend
- [X] accounted for nearly half of the total

Weak structures to avoid:
- rose
- a sentence about data
- this is a good phrase
- something increased
- data changed a lot over time

### OUTPUT REQUIREMENTS ###
- Return between 3 and 10 items.
- Only return genuinely useful IELTS Writing Task 1 language.
- Each item must contain exactly these fields:
  - category
  - subcategory
  - structure
  - example

### FINAL REMINDER ###
- Use the existing taxonomy as much as possible.
- Reuse existing subcategories whenever they are even reasonably suitable.
- Only add a new subcategory if it is truly necessary and clearly non-duplicative.
- Write "structure" in a way that a real IELTS learner would want to save and study.
"""

    user_content = f"""
Essay to analyse:

{essay}

Extract the most useful learnable language units from this IELTS Writing Task 1 essay.

Requirements:
- classify each item using the taxonomy
- use an existing subcategory whenever possible
- only create a new subcategory if absolutely necessary
- write each structure as a reusable IELTS study template with placeholders such as [X], [Y], [sth], [the figure], [the number of ...]
- use an exact example taken from the essay
- return only high-quality items
"""

    writer("📚 Extracting vocabulary, collocations, and structures...")
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    result = model.invoke(messages)

    if not isinstance(result, LanguageExtractionResult):
        result = LanguageExtractionResult(items=[])

    items = result.items if result.items else []
    writer(f"✅ Extracted {len(items)} language unit(s) for human review.")

    return {
        "final_generated_essay": essay,
        "proposed_language_items": [item.model_dump() for item in items],
    }
