"""HITL Node: Human-in-the-Loop review for proposed language units."""

from langgraph.types import StreamWriter, interrupt

from schemas.state import JihanState


def _format_item(item: dict, idx: int) -> str:
    """Format a single proposed language item for display."""
    cat = item.get("category", "")
    sub = item.get("subcategory", "")
    struct = item.get("structure", "")
    ex = item.get("example", "")
    return (
        f"[{idx}] category: {cat}\n"
        f"    subcategory: {sub}\n"
        f"    structure: {struct}\n"
        f"    example: {ex}"
    )


def hitl_review_extractions_node(
    state: JihanState,
    *,
    writer: StreamWriter,
) -> dict:
    """
    Human-in-the-Loop node for reviewing proposed language units.
    Displays items for human approval before they are written to the database.
    """
    writer("👤 Human Review: Proposed language units ready for approval...")

    proposed = state.get("proposed_language_items") or []

    if proposed:
        writer("\n" + "=" * 60)
        writer("📚 PROPOSED LANGUAGE UNITS FOR REVIEW")
        writer("=" * 60)
        for i, item in enumerate(proposed, 1):
            if isinstance(item, dict):
                writer(f"\n{_format_item(item, i)}")
            else:
                writer(f"\n[{i}] {item}")
        writer("\n" + "=" * 60)

    writer("⏸️  Workflow paused. Approve or reject each item (in main loop)...")
    interrupt("Waiting for human to approve or reject proposed language units")

    writer("▶️  Resuming workflow with approved items...")

    return {"human_review_extractions": True}
