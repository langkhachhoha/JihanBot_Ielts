"""
JihanBot - IELTS Writing Task 1 Generator
Main app for testing the pipeline with custom streaming and HITL support.
"""

import json
from pathlib import Path

from dotenv import load_dotenv

from graph.workflow import create_jihan_graph
from schemas.state import JihanState, ExtractedFeatures, GradingFeedback

# Load environment
load_dotenv(Path(__file__).parent / ".env")


def _prompt_user_for_features(current_features):
    """Prompt user to review and potentially edit extracted features."""
    print("\n" + "=" * 60)
    print("👤 HUMAN REVIEW - EXTRACTED FEATURES")
    print("=" * 60)
    print("Options:")
    print("  1. Accept as-is (press Enter)")
    print("  2. Edit features (type 'edit')")
    print("=" * 60)
    
    choice = input("\nYour choice: ").strip().lower()
    
    if choice == "edit":
        print("\nEnter updated features (or press Enter to keep current):")
        print("-" * 60)
        
        overview = input(f"Overview [{current_features.overview[:50]}...]: ").strip()
        paragraph_1 = input(f"Paragraph 1 [{current_features.paragraph_1[:50]}...]: ").strip()
        paragraph_2 = input(f"Paragraph 2 [{current_features.paragraph_2[:50]}...]: ").strip()
        grouping_logic = input(f"Grouping Logic [{current_features.grouping_logic[:50]}...]: ").strip()
        
        updated_features = ExtractedFeatures(
            overview=overview if overview else current_features.overview,
            paragraph_1=paragraph_1 if paragraph_1 else current_features.paragraph_1,
            paragraph_2=paragraph_2 if paragraph_2 else current_features.paragraph_2,
            grouping_logic=grouping_logic if grouping_logic else current_features.grouping_logic,
        )
        
        print("\n✅ Features updated!")
        return updated_features
    
    print("\n✅ Features accepted as-is!")
    return current_features


def _prompt_user_for_grading(current_feedback):
    """Prompt user to review and potentially edit grading feedback."""
    print("\n" + "=" * 60)
    print("👤 HUMAN REVIEW - GRADING FEEDBACK")
    print("=" * 60)
    print("Options:")
    print("  1. Accept as-is (press Enter)")
    print("  2. Accept essay without revision (type 'accept')")
    print("  3. Edit feedback (type 'edit')")
    print("=" * 60)
    
    choice = input("\nYour choice: ").strip().lower()
    
    if choice == "accept":
        print("\n✅ Essay accepted! Skipping revision.")
        return GradingFeedback(
            passed=True,
            task_achievement_feedback="",
            coherence_cohesion_feedback="",
            lexical_resource_feedback="",
            grammatical_range_feedback="",
            suggestion="",
            overall_score=current_feedback.overall_score if hasattr(current_feedback, "overall_score") else 0.0,
        )
    
    elif choice == "edit":
        print("\nEnter updated feedback (or press Enter to keep current):")
        print("-" * 60)
        
        passed_input = input(f"Passed [{'Yes' if current_feedback.passed else 'No'}] (yes/no): ").strip().lower()
        passed = passed_input == "yes" if passed_input else current_feedback.passed
        
        ta_feedback = input(f"Task Achievement feedback: ").strip()
        cc_feedback = input(f"Coherence & Cohesion feedback: ").strip()
        lr_feedback = input(f"Lexical Resource feedback: ").strip()
        gr_feedback = input(f"Grammatical Range feedback: ").strip()
        suggestion = input(f"Suggestions: ").strip()
        
        updated_feedback = GradingFeedback(
            passed=passed,
            task_achievement_feedback=ta_feedback if ta_feedback else current_feedback.task_achievement_feedback,
            coherence_cohesion_feedback=cc_feedback if cc_feedback else current_feedback.coherence_cohesion_feedback,
            lexical_resource_feedback=lr_feedback if lr_feedback else current_feedback.lexical_resource_feedback,
            grammatical_range_feedback=gr_feedback if gr_feedback else current_feedback.grammatical_range_feedback,
            suggestion=suggestion if suggestion else current_feedback.suggestion,
            overall_score=current_feedback.overall_score,
        )
        
        print("\n✅ Feedback updated!")
        return updated_feedback
    
    print("\n✅ Feedback accepted as-is!")
    return current_feedback


def _get_items_path(taxonomy_path: str) -> Path:
    """Derive items file path from taxonomy path: same directory, language_items.json."""
    return Path(taxonomy_path).parent / "language_items.json"


def _append_items_to_database(taxonomy_path: str, items: list) -> None:
    """Append approved language items to language_items.json (separate from taxonomy).
    Items are organized/sorted by category, then subcategory for readability."""
    if not taxonomy_path or not items:
        return
    items_path = _get_items_path(taxonomy_path)
    try:
        existing = []
        if items_path.exists():
            with open(items_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                existing = data.get("items", [])
        merged = existing + items
        merged.sort(key=lambda x: (x.get("category", ""), x.get("subcategory", "")))
        data = {"items": merged}
        with open(items_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except (json.JSONDecodeError, OSError):
        pass


def _truncate(s: str, max_len: int = 60) -> str:
    """Truncate string for display, add ... if longer."""
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def _prompt_edit_item(item: dict) -> dict:
    """Prompt user to edit a language item's fields."""
    cat = item.get("category", "")
    sub = item.get("subcategory", "")
    struct = item.get("structure", "")
    ex = item.get("example", "")
    print("    Enter new values (or press Enter to keep current):")
    new_cat = input(f"    category [{cat}]: ").strip() or cat
    new_sub = input(f"    subcategory [{sub}]: ").strip() or sub
    new_struct = input(f"    structure [{_truncate(struct)}]: ").strip() or struct
    new_ex = input(f"    example [{_truncate(ex)}]: ").strip() or ex
    return {"category": new_cat, "subcategory": new_sub, "structure": new_struct, "example": new_ex}


def _prompt_user_for_extractions(proposed: list, taxonomy_path: str) -> list:
    """Prompt user to approve, reject, or edit each proposed language item. Write approved to language_items.json."""
    if not proposed:
        return []
    print("\n" + "=" * 60)
    print("👤 HUMAN REVIEW - PROPOSED LANGUAGE UNITS")
    print("=" * 60)
    print("For each item: approve (y), reject (n), or edit (edit).")
    print("=" * 60)

    approved = []
    for i, item in enumerate(proposed, 1):
        if not isinstance(item, dict):
            item = {"category": "", "subcategory": "", "structure": str(item), "example": ""}
        while True:
            cat = item.get("category", "")
            sub = item.get("subcategory", "")
            struct = item.get("structure", "")
            ex = item.get("example", "")
            print(f"\n[{i}] category: {cat} | subcategory: {sub}")
            print(f"    structure: {struct}")
            print(f"    example: {ex}")
            choice = input("    Add to database? (y/n/edit) [n]: ").strip().lower()
            if choice == "y":
                approved.append(item)
                break
            elif choice == "edit":
                item = _prompt_edit_item(item)
                print("    Item updated. Review again:")
            else:
                break

    if approved and taxonomy_path:
        _append_items_to_database(taxonomy_path, approved)
        items_path = _get_items_path(taxonomy_path)
        print(f"\n✅ {len(approved)} item(s) written to {items_path}.")
    elif approved:
        print(f"\n✅ {len(approved)} item(s) approved (no taxonomy path set).")
    else:
        print("\n✅ No items approved.")

    return approved


def run_jihan_bot(image_path: str, band_score: str = "7", database_path: str | None = None):
    """
    Run JihanBot pipeline with HITL support and custom streaming.

    Args:
        image_path: Path to IELTS Task 1 question image (local file)
        band_score: Target IELTS band (e.g., "6", "7", "8")
        database_path: Path to taxonomy JSON (default: data/language_taxonomy.json).
                      Approved items are stored in language_items.json in the same directory.
    """
    graph = create_jihan_graph()

    default_db_path = str(Path(__file__).parent / "data" / "language_taxonomy.json")
    db_path = database_path or default_db_path

    initial_state: JihanState = {
        "image_path": image_path,
        "band_score": band_score,
        "raw_question": "",
        "extracted_features": None,
        "extraction_feedback": None,
        "extraction_retry_count": 0,
        "essay": "",
        "grading_feedback": None,
        "grading_retry_count": 0,
        "human_review_features": None,
        "human_review_grading": None,
        "database_path": db_path,
        "final_generated_essay": None,
        "proposed_language_items": None,
        "approved_language_items": None,
        "human_review_extractions": None,
    }

    config = {"configurable": {"thread_id": "jihan-1"}}

    print("=" * 60)
    print("🚀 JihanBot - IELTS Writing Task 1 Generator (with HITL)")
    print("=" * 60)
    print(f"Image: {image_path}")
    print(f"Target Band: {band_score}")
    print("=" * 60)

    # Track if this is the first run
    first_run = True
    
    # Main loop: handle streaming and interrupts
    while True:
        # Stream until interrupt or completion
        # On first run, pass initial_state; on subsequent runs, pass None to resume
        stream_input = initial_state if first_run else None
        first_run = False
        
        for chunk in graph.stream(
            stream_input,
            config=config,
            stream_mode=["custom", "messages"],
        ):
            # Chunk format: (mode, data) or (namespace, mode, data)
            if isinstance(chunk, tuple):
                if len(chunk) == 3:
                    _ns, mode, data = chunk
                else:
                    mode, data = chunk
                if mode == "custom" and data:
                    print(data)
                elif mode == "messages" and data:
                    msg, _meta = data
                    content = getattr(msg, "content", None) or ""
                    if isinstance(content, str) and content:
                        print(content, end="", flush=True)
            elif chunk:
                print(chunk)

        # Check current state
        state = graph.get_state(config)
        
        # If no more nodes to execute, workflow is complete
        if not state.next:
            break
        
        # Handle interrupts
        state_values = state.values if hasattr(state, "values") else {}
        
        if "hitl_review_features" in state.next:
            # Human review for extracted features
            current_features = state_values.get("extracted_features")
            if current_features:
                updated_features = _prompt_user_for_features(current_features)
                
                # Update state with reviewed features
                graph.update_state(
                    config,
                    {"extracted_features": updated_features},
                    as_node="hitl_review_features"
                )
        
        elif "hitl_review_grading" in state.next:
            # Human review for grading feedback
            current_feedback = state_values.get("grading_feedback")
            if current_feedback:
                updated_feedback = _prompt_user_for_grading(current_feedback)
                
                # Update state with reviewed feedback
                graph.update_state(
                    config,
                    {"grading_feedback": updated_feedback},
                    as_node="hitl_review_grading"
                )

        elif "hitl_review_extractions" in state.next:
            # Human review for proposed language units
            proposed = state_values.get("proposed_language_items") or []
            db_path = state_values.get("database_path") or ""
            approved = _prompt_user_for_extractions(proposed, db_path)
            graph.update_state(
                config,
                {"approved_language_items": approved},
                as_node="hitl_review_extractions"
            )

    # Get final state
    final_state = graph.get_state(config)
    state_values = final_state.values if hasattr(final_state, "values") else {}

    print("\n" + "=" * 60)
    print("📝 FINAL ESSAY")
    print("=" * 60)
    essay = state_values.get("essay", "")
    if essay:
        print(essay)
    else:
        print("No essay generated.")
    print("=" * 60)

    return state_values


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_ielts_task1_image> [band_score] [database_path]")
        print("Example: python main.py ./sample_ielts_task1.png 7")
        sys.exit(1)

    image_path = sys.argv[1]
    band_score = sys.argv[2] if len(sys.argv) > 2 else "7"
    database_path = sys.argv[3] if len(sys.argv) > 3 else None

    if not Path(image_path).exists():
        print(f"Error: Image not found: {image_path}")
        sys.exit(1)

    run_jihan_bot(image_path, band_score, database_path)
