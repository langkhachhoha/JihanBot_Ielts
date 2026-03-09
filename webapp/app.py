"""
JihanBot Web Demo - FastAPI backend.
Runs the Jihan graph with SSE streaming and HITL support.
Does not modify any existing Jihan files.
"""

import asyncio
import json
import os
import sys
import tempfile
import threading
import uuid
from pathlib import Path
from queue import Empty, Queue

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

# Add Jihan parent to path and load env before importing Jihan modules
JIHAN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(JIHAN_ROOT))
load_dotenv(JIHAN_ROOT / ".env")

from graph.workflow import create_jihan_graph
from schemas.state import ExtractedFeatures, GradingFeedback, JihanState

app = FastAPI(title="JihanBot Web Demo")

sessions: dict[str, dict] = {}
sessions_lock = threading.Lock()

DEFAULT_DB_PATH = str(JIHAN_ROOT / "data" / "language_taxonomy.json")
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


def _get_items_path(taxonomy_path: str) -> Path:
    """Derive items file path from taxonomy path."""
    return Path(taxonomy_path).parent / "language_items.json"


def _append_items_to_database(taxonomy_path: str, items: list) -> None:
    """Append approved language items to language_items.json."""
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


def _obj_to_dict(obj):
    """Convert pydantic model or object to JSON-serializable dict."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "model_dump_json"):
        return json.loads(obj.model_dump_json())
    if isinstance(obj, dict):
        return {k: _obj_to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_obj_to_dict(x) for x in obj]
    return obj


def _run_graph_session(thread_id: str, image_path: str, band_score: str, db_path: str):
    """Run Jihan graph in a background thread. Puts events in session queue."""
    session = sessions.get(thread_id)
    if not session:
        return
    queue = session["queue"]
    graph = session["graph"]
    config = session["config"]

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

    first_run = True
    while True:
        stream_input = initial_state if first_run else None
        first_run = False

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
                    queue.put({"type": "thinking", "text": data})
                # Skip "messages" - they stream token-by-token and fragment the thinking display

        state = graph.get_state(config)
        if not state.next:
            state_values = state.values if hasattr(state, "values") else state
            queue.put({
                "type": "done",
                "state": _obj_to_dict(dict(state_values)) if state_values else {},
            })
            session["done"] = True
            return

        state_values = state.values if hasattr(state, "values") else state
        state_dict = _obj_to_dict(dict(state_values)) if state_values else {}
        next_nodes = list(state.next) if hasattr(state.next, "__iter__") else [state.next]

        # Store for HITL endpoints (e.g. skip_revision needs overall_score)
        with sessions_lock:
            session["last_interrupt_state"] = state_dict
            session["database_path"] = state_dict.get("database_path") or db_path

        if "hitl_review_features" in next_nodes:
            queue.put({
                "type": "interrupt",
                "node": "hitl_review_features",
                "state": state_dict,
            })
            with session["condition"]:
                session["condition"].wait()
        elif "hitl_review_grading" in next_nodes:
            queue.put({
                "type": "interrupt",
                "node": "hitl_review_grading",
                "state": state_dict,
            })
            with session["condition"]:
                session["condition"].wait()
        elif "hitl_review_extractions" in next_nodes:
            queue.put({
                "type": "interrupt",
                "node": "hitl_review_extractions",
                "state": state_dict,
            })
            with session["condition"]:
                session["condition"].wait()


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main demo page."""
    html_path = Path(__file__).parent / "static" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/api/gallery")
async def get_gallery():
    """Return language_items + taxonomy metadata for the gallery."""
    taxonomy_path = Path(DEFAULT_DB_PATH)
    items_path = _get_items_path(str(taxonomy_path))
    taxonomy = {}
    items = []
    if taxonomy_path.exists():
        with open(taxonomy_path, "r", encoding="utf-8") as f:
            taxonomy = json.load(f)
    if items_path.exists():
        with open(items_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            items = data.get("items", [])
    return {"taxonomy": taxonomy, "items": items}


@app.post("/api/run")
async def run_pipeline(
    image: UploadFile = File(...),
    band_score: str = Form("7"),
):
    """Start the Jihan pipeline. Returns thread_id for SSE streaming."""
    suffix = Path(image.filename or "image.png").suffix.lower()
    if suffix not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        suffix = ".png"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=UPLOAD_DIR)
    try:
        content = await image.read()
        tmp.write(content)
        tmp.close()
        image_path = tmp.name
    except Exception:
        tmp.close()
        os.unlink(tmp.name)
        raise

    thread_id = str(uuid.uuid4())
    graph = create_jihan_graph()
    queue: Queue = Queue()
    condition = threading.Condition()

    with sessions_lock:
        sessions[thread_id] = {
            "queue": queue,
            "condition": condition,
            "graph": graph,
            "config": {"configurable": {"thread_id": thread_id}},
            "image_path": image_path,
            "done": False,
        }

    t = threading.Thread(
        target=_run_graph_session,
        args=(thread_id, image_path, band_score, DEFAULT_DB_PATH),
        daemon=True,
    )
    t.start()

    return JSONResponse({"thread_id": thread_id})


async def _sse_generator(thread_id: str):
    """Async generator for SSE events from session queue."""
    session = sessions.get(thread_id)
    if not session:
        yield ServerSentEvent(data=json.dumps({"error": "Invalid thread_id"}), event="error")
        return
    queue = session["queue"]
    loop = asyncio.get_running_loop()

    while not session.get("done", False):
        try:
            item = await loop.run_in_executor(None, lambda: queue.get(timeout=2))
        except Empty:
            yield ServerSentEvent(data="", event="ping")
            continue

        if item.get("type") == "thinking":
            yield ServerSentEvent(data=json.dumps({"text": item["text"]}), event="thinking")
        elif item.get("type") == "interrupt":
            yield ServerSentEvent(data=json.dumps(item), event="interrupt")
            break
        elif item.get("type") == "done":
            yield ServerSentEvent(data=json.dumps(item), event="done")
            return

    # After interrupt, wait for more events (graph continues after HITL)
    for _ in range(300):
        try:
            item = await loop.run_in_executor(None, lambda: queue.get(timeout=2))
        except Empty:
            yield ServerSentEvent(data="", event="ping")
            continue
        if item.get("type") == "thinking":
            yield ServerSentEvent(data=json.dumps({"text": item["text"]}), event="thinking")
        elif item.get("type") == "done":
            yield ServerSentEvent(data=json.dumps(item), event="done")
            return


@app.get("/api/stream/{thread_id}")
async def stream_events(thread_id: str):
    """SSE endpoint for real-time thinking and interrupt events."""
    if thread_id not in sessions:
        return JSONResponse({"error": "Invalid thread_id"}, status_code=404)
    return EventSourceResponse(_sse_generator(thread_id))


def _apply_hitl_and_continue(thread_id: str, node: str, update: dict):
    """Apply HITL update and resume graph."""
    session = sessions.get(thread_id)
    if not session:
        raise ValueError("Invalid thread_id")
    graph = session["graph"]
    config = session["config"]

    if node == "hitl_review_features" and "extracted_features" in update:
        ef = update["extracted_features"]
        if isinstance(ef, dict):
            update["extracted_features"] = ExtractedFeatures(**ef)
    elif node == "hitl_review_grading" and "grading_feedback" in update:
        gf = update["grading_feedback"]
        if isinstance(gf, dict):
            update["grading_feedback"] = GradingFeedback(**gf)

    graph.update_state(config, update, as_node=node)
    with session["condition"]:
        session["condition"].notify_all()


@app.post("/api/hitl/features")
async def hitl_features(
    thread_id: str = Form(...),
    overview: str = Form(""),
    paragraph_1: str = Form(""),
    paragraph_2: str = Form(""),
    grouping_logic: str = Form(""),
):
    """Submit reviewed extracted features and continue pipeline."""
    if thread_id not in sessions:
        return JSONResponse({"error": "Invalid thread_id"}, status_code=404)
    session = sessions[thread_id]
    state = session.get("last_interrupt_state", {})
    ef = state.get("extracted_features") or {}
    if isinstance(ef, dict):
        overview = overview if overview else ef.get("overview", "")
        paragraph_1 = paragraph_1 if paragraph_1 else ef.get("paragraph_1", "")
        paragraph_2 = paragraph_2 if paragraph_2 else ef.get("paragraph_2", "")
        grouping_logic = grouping_logic if grouping_logic else ef.get("grouping_logic", "")
    update = {
        "extracted_features": ExtractedFeatures(
            overview=overview,
            paragraph_1=paragraph_1,
            paragraph_2=paragraph_2,
            grouping_logic=grouping_logic,
        )
    }
    try:
        _apply_hitl_and_continue(thread_id, "hitl_review_features", update)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/hitl/grading")
async def hitl_grading(
    thread_id: str = Form(...),
    action: str = Form("accept"),
    passed: str = Form("true"),
    task_achievement_feedback: str = Form(""),
    coherence_cohesion_feedback: str = Form(""),
    lexical_resource_feedback: str = Form(""),
    grammatical_range_feedback: str = Form(""),
    suggestion: str = Form(""),
    overall_score: str = Form("0"),
):
    """Submit reviewed grading feedback and continue pipeline."""
    if thread_id not in sessions:
        return JSONResponse({"error": "Invalid thread_id"}, status_code=404)
    session = sessions[thread_id]
    state = session.get("last_interrupt_state", {})
    gf = state.get("grading_feedback") or {}

    if action == "skip_revision":
        scr = float(gf.get("overall_score", 0) or 0)
        update = {
            "grading_feedback": GradingFeedback(
                passed=True,
                task_achievement_feedback="",
                coherence_cohesion_feedback="",
                lexical_resource_feedback="",
                grammatical_range_feedback="",
                suggestion="",
                overall_score=scr,
            )
        }
    else:
        if isinstance(gf, dict):
            task_achievement_feedback = task_achievement_feedback or gf.get("task_achievement_feedback", "")
            coherence_cohesion_feedback = coherence_cohesion_feedback or gf.get("coherence_cohesion_feedback", "")
            lexical_resource_feedback = lexical_resource_feedback or gf.get("lexical_resource_feedback", "")
            grammatical_range_feedback = grammatical_range_feedback or gf.get("grammatical_range_feedback", "")
            suggestion = suggestion or gf.get("suggestion", "")
            overall_score = overall_score or str(gf.get("overall_score", 0) or 0)
        update = {
            "grading_feedback": GradingFeedback(
                passed=passed.lower() in ("true", "1", "yes"),
                task_achievement_feedback=task_achievement_feedback,
                coherence_cohesion_feedback=coherence_cohesion_feedback,
                lexical_resource_feedback=lexical_resource_feedback,
                grammatical_range_feedback=grammatical_range_feedback,
                suggestion=suggestion,
                overall_score=float(overall_score or 0),
            )
        }
    try:
        _apply_hitl_and_continue(thread_id, "hitl_review_grading", update)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/hitl/extractions")
async def hitl_extractions(thread_id: str = Form(...), body: str = Form("[]")):
    """Submit approved language items and continue pipeline."""
    if thread_id not in sessions:
        return JSONResponse({"error": "Invalid thread_id"}, status_code=404)
    try:
        approved = json.loads(body) if isinstance(body, str) else body
        if not isinstance(approved, list):
            approved = []
    except json.JSONDecodeError:
        approved = []

    session = sessions[thread_id]
    db_path = session.get("database_path") or DEFAULT_DB_PATH
    _append_items_to_database(db_path, approved)

    update = {"approved_language_items": approved}
    try:
        _apply_hitl_and_continue(thread_id, "hitl_review_extractions", update)
        return JSONResponse({"ok": True, "saved": len(approved)})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
