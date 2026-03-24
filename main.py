"""
JihanBot v2 — IELTS Writing Task 1/2: generate and/or grade with one HITL planning step.
"""

import argparse
from pathlib import Path

from dotenv import load_dotenv

from graph.workflow import create_jihan_graph
from schemas.state import JihanState

load_dotenv(Path(__file__).parent / ".env")


def _read_text_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _prompt_multiline(lead: str) -> str:
    print(lead)
    print("(Finish with a line containing only ###)")
    lines: list[str] = []
    while True:
        line = input()
        if line.strip() == "###":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _collect_planning_interactive(state_values: dict) -> dict:
    print("\n" + "=" * 60)
    print("HUMAN PLANNING (HITL)")
    print("=" * 60)
    print("Task:", state_values.get("task_type"))
    print("Prompt kind:", state_values.get("prompt_kind"))
    t = (state_values.get("source_prompt_text") or "")[:500]
    if t:
        print("Prompt text (preview):\n", t, "..." if len(state_values.get("source_prompt_text") or "") > 500 else "", sep="")
    print("=" * 60)
    mode_in = input("Mode — 1 = generate new essay, 2 = grade my essay only [1]: ").strip() or "1"
    user_mode = "grade_only" if mode_in == "2" else "generate"
    band = input("Target band (e.g. 6.5) [7]: ").strip() or "7"

    user_outline = ""
    user_essay = ""
    essay_under_review = ""

    if user_mode == "generate":
        want = input("Optional outline / plan (y/n) [n]: ").strip().lower()
        if want == "y":
            user_outline = _prompt_multiline("Paste your outline:")
    else:
        user_essay = _prompt_multiline("Paste your essay to grade:")
        essay_under_review = user_essay

    return {
        "user_mode": user_mode,
        "target_band": band,
        "user_outline": user_outline or None,
        "user_essay": user_essay or None,
        "essay_under_review": essay_under_review,
    }


def build_initial_state(args: argparse.Namespace) -> JihanState:
    text = args.text
    if args.text_file:
        text = _read_text_file(args.text_file)
    return {
        "task_type": args.task,
        "prompt_kind": args.prompt_kind,
        "source_image_path": args.image,
        "source_prompt_text": text or "",
        "user_mode": None,
        "target_band": args.band,
        "user_outline": None,
        "user_essay": None,
        "refined_brief": None,
        "generated_essay": None,
        "essay_under_review": "",
        "grading_output": None,
        "human_review_planning": None,
    }


def run_jihan_v2(args: argparse.Namespace) -> dict:
    graph = create_jihan_graph()
    config = {"configurable": {"thread_id": args.thread_id}}
    initial_state = build_initial_state(args)

    print("=" * 60)
    print("JihanBot v2 — IELTS Writing")
    print("=" * 60)

    first = True
    while True:
        stream_input = initial_state if first else None
        first = False
        for chunk in graph.stream(
            stream_input,
            config=config,
            stream_mode=["custom", "messages"],
        ):
            if isinstance(chunk, tuple):
                if len(chunk) == 3:
                    _ns, mode, data = chunk
                else:
                    mode, data = chunk
                if mode == "custom" and data:
                    print(data)

        state = graph.get_state(config)
        if not state.next:
            break

        next_nodes = list(state.next) if hasattr(state.next, "__iter__") else [state.next]
        if "hitl_planning" in next_nodes:
            values = dict(state.values) if state.values else {}
            update = _collect_planning_interactive(values)
            graph.update_state(config, update, as_node="hitl_planning")
        else:
            break

    final = graph.get_state(config)
    out = dict(final.values) if final.values else {}
    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)
    go = out.get("grading_output")
    if go is not None:
        if hasattr(go, "model_dump"):
            gd = go.model_dump()
        else:
            gd = dict(go) if isinstance(go, dict) else {}
        print("Overall task band:", gd.get("overall_task_band"))
        print("Refined essay:\n", gd.get("refined_essay", ""))
    else:
        print("No grading output.")
    print("=" * 60)
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="JihanBot v2 CLI")
    p.add_argument("--task", choices=["task_1", "task_2"], default="task_1", help="IELTS task")
    p.add_argument("--image", default=None, help="Path to task image (optional)")
    p.add_argument("--text", default="", help="Task prompt as inline text")
    p.add_argument("--text-file", default=None, help="Read task prompt from UTF-8 file")
    p.add_argument(
        "--prompt-kind",
        choices=["image", "text", "image_text"],
        default=None,
        help="Override prompt kind (default: inferred from image/text)",
    )
    p.add_argument("--band", default="7", help="Default target band (can override in HITL)")
    p.add_argument("--thread-id", default="cli-1", help="Checkpoint thread id")
    args = p.parse_args()
    if args.prompt_kind:
        pk = args.prompt_kind
    else:
        has_img = bool(args.image)
        has_txt = bool((args.text or "").strip() or args.text_file)
        if has_img and has_txt:
            pk = "image_text"
        elif has_img:
            pk = "image"
        else:
            pk = "text"
    args.prompt_kind = pk

    if args.prompt_kind in ("image", "image_text") and not args.image:
        p.error("--image required for image / image_text prompt kind")
    if args.prompt_kind == "text" and not (args.text or "").strip() and not args.text_file:
        p.error("Provide --text or --text-file for text-only prompt kind")

    run_jihan_v2(args)


if __name__ == "__main__":
    main()
