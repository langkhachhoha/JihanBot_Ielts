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

    system_prompt = f"""You are an expert IELTS tutor and linguist. Extract learnable language units from an IELTS Writing Task 1 essay. Focus on: topic vocabulary, collocations, sentence structures, and expression patterns worth studying.

### TAXONOMY (categories and subcategories - YOU MUST USE THESE) ###
{taxonomy_str}

### STRICT RULES ###
1. category: MUST be one of the category names listed above. DO NOT create new categories.
2. subcategory: PREFER choosing from the subcategories listed for that category. You may propose a NEW subcategory ONLY if:
   - No existing subcategory fits well
   - The new subcategory does NOT duplicate an existing one in meaning
   - The new subcategory logically belongs to its category
3. structure: A clear, generalisable pattern or template (e.g. "Sth increased significantly over the period").
4. example: MUST be taken verbatim or as a short excerpt from the essay. Quote the actual sentence/phrase from the text.

### OUTPUT ###
Return 3-10 high-quality items. Prioritise academic vocabulary, strong collocations, varied sentence patterns, and useful IELTS Task 1 expressions. Each item must have exactly: category, subcategory, structure, example."""

    user_content = f"""Essay to analyze:

{essay}

Extract learnable language units. Classify each using the taxonomy above. Example must be from the essay."""

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
