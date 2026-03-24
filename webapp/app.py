"""
JihanBot v2 Web Demo — FastAPI backend with SSE and HITL planning.
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

JIHAN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(JIHAN_ROOT))
load_dotenv(JIHAN_ROOT / ".env")

from graph.workflow import create_jihan_graph
from schemas.state import JihanState

app = FastAPI(title="JihanBot v2 Web Demo")

sessions: dict[str, dict] = {}
sessions_lock = threading.Lock()

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


def _obj_to_dict(obj):
    """Convert pydantic model or object to JSON-serializable dict."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return {k: _obj_to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_obj_to_dict(x) for x in obj]
    return obj


def _infer_prompt_kind(has_image: bool, prompt_text: str) -> str:
    t = (prompt_text or "").strip()
    if has_image and t:
        return "image_text"
    if has_image:
        return "image"
    return "text"


def _run_graph_session(thread_id: str, initial_state: JihanState):
    """Run Jihan graph in a background thread."""
    session = sessions.get(thread_id)
    if not session:
        return
    queue = session["queue"]
    graph = session["graph"]
    config = session["config"]

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

        with sessions_lock:
            session["last_interrupt_state"] = state_dict

        if "hitl_planning" in next_nodes:
            queue.put({
                "type": "interrupt",
                "node": "hitl_planning",
                "state": state_dict,
            })
            with session["condition"]:
                session["condition"].wait()
        else:
            queue.put({
                "type": "done",
                "state": state_dict,
            })
            session["done"] = True
            return


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).parent / "static" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/api/run")
async def run_pipeline(
    task_type: str = Form("task_1"),
    band_score: str = Form("7"),
    prompt_text: str = Form(""),
    image: UploadFile | None = File(None),
):
    """Start v2 pipeline. Returns thread_id for SSE."""
    if task_type not in ("task_1", "task_2"):
        return JSONResponse({"error": "task_type must be task_1 or task_2"}, status_code=400)

    image_path = None
    if image is not None and image.filename:
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
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)
            raise

    has_image = bool(image_path)
    prompt_kind = _infer_prompt_kind(has_image, prompt_text)

    if prompt_kind in ("image", "image_text") and not image_path:
        return JSONResponse(
            {"error": "Image required for this prompt (or provide text-only task)."},
            status_code=400,
        )
    if prompt_kind == "text" and not (prompt_text or "").strip():
        return JSONResponse(
            {"error": "prompt_text required for text-only runs."},
            status_code=400,
        )

    initial_state: JihanState = {
        "task_type": task_type,
        "prompt_kind": prompt_kind,
        "source_image_path": image_path,
        "source_prompt_text": prompt_text or "",
        "user_mode": None,
        "target_band": band_score,
        "user_outline": None,
        "user_essay": None,
        "refined_brief": None,
        "generated_essay": None,
        "essay_under_review": "",
        "grading_output": None,
        "human_review_planning": None,
    }

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
            "done": False,
        }

    t = threading.Thread(
        target=_run_graph_session,
        args=(thread_id, initial_state),
        daemon=True,
    )
    t.start()

    return JSONResponse({"thread_id": thread_id})


async def _sse_generator(thread_id: str):
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

    for _ in range(600):
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
    if thread_id not in sessions:
        return JSONResponse({"error": "Invalid thread_id"}, status_code=404)
    return EventSourceResponse(_sse_generator(thread_id))


def _apply_hitl_and_continue(thread_id: str, node: str, update: dict):
    session = sessions.get(thread_id)
    if not session:
        raise ValueError("Invalid thread_id")
    graph = session["graph"]
    config = session["config"]
    graph.update_state(config, update, as_node=node)
    with session["condition"]:
        session["condition"].notify_all()


@app.post("/api/hitl/planning")
async def hitl_planning(
    thread_id: str = Form(...),
    user_mode: str = Form("generate"),
    target_band: str = Form("7"),
    user_outline: str = Form(""),
    user_essay: str = Form(""),
):
    if thread_id not in sessions:
        return JSONResponse({"error": "Invalid thread_id"}, status_code=404)
    if user_mode not in ("generate", "grade_only"):
        return JSONResponse({"error": "user_mode must be generate or grade_only"}, status_code=400)

    essay_under_review = ""
    if user_mode == "grade_only":
        essay_under_review = (user_essay or "").strip()
        if not essay_under_review:
            return JSONResponse({"error": "user_essay required for grade_only"}, status_code=400)

    update = {
        "user_mode": user_mode,
        "target_band": target_band.strip() or "7",
        "user_outline": user_outline.strip() or None,
        "user_essay": user_essay.strip() or None,
        "essay_under_review": essay_under_review,
    }
    try:
        _apply_hitl_and_continue(thread_id, "hitl_planning", update)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
