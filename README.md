# JihanBot

Generates IELTS Writing Task 1 essays from chart images via LangGraph, with human-in-the-loop review at three checkpoints and a language structure gallery for reusable phrasing.

## Pipeline

![Pipeline diagram](pipeline-diagram.png)

Flow: extract question → extract features → **HITL features** → verify extraction → write essay → grade essay → **HITL grading** → extract language units → **HITL extractions** → done. Each HITL step pauses for review and edits before continuing.

## Project structure

```
Jihan/
├── pipeline-diagram.png
├── main.py                    # CLI entry
├── config.py                  # Model config (vision, text)
├── requirements.txt
├── graph/
│   └── workflow.py
├── agents/
│   ├── extract_question_agent.py
│   ├── extract_features_agent.py
│   ├── verify_extraction_agent.py
│   ├── write_essay_agent.py
│   ├── grade_essay_agent.py
│   ├── extract_language_units_agent.py
│   ├── hitl_review_features_node.py
│   ├── hitl_review_grading_node.py
│   └── hitl_review_extractions_node.py
├── schemas/
│   └── state.py               # JihanState, ExtractedFeatures, GradingFeedback
├── data/
│   ├── language_taxonomy.json  # Category/subcategory for language units
│   └── language_items.json     # Approved language structures
├── utils/
│   └── image.py
└── webapp/                     # FastAPI demo
    ├── app.py
    ├── requirements.txt
    ├── static/
    │   ├── index.html
    │   ├── styles.css
    │   └── app.js
    └── uploads/
```

## CLI

```bash
cd Jihan
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set:

| Variable | Purpose |
|----------|---------|
| `TOGETHER_API_KEY` | Vision + text models (Together) |
| `OPENAI_API_KEY` | Language extraction (GPT-4o) |

```bash
python main.py <image_path> [band_score] [database_path]
```

Example:

```bash
python main.py ./image.png 7
python main.py ./task1_chart.png 7.5
```

## Web demo

![Web demo screenshot](webapp/screenshot.png)

Upload a chart image, stream thinking logs, receive the essay, and perform HITL at three review points. Approved language units are saved to the gallery.

| Section | Description |
|---------|-------------|
| **Upload** | Drag & drop image, choose band 6.0–8.5, click Generate Essay |
| **Thinking** | Real-time status log |
| **Final Essay** | Output after pipeline completes |
| **Proposed Language Units** | Review → Edit/Approve/Reject → Save Approved |
| **Language Gallery** | Open → grid by category, filter, Close |

Design: dark theme (#0f1419, #1e2a3a), blue accent (#3b82f6). Fonts: Fraunces, Source Sans 3, JetBrains Mono.

```bash
cd Jihan/webapp
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0
```

Then open http://localhost:8000.

### API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | / | Home |
| GET | /api/gallery | Taxonomy + items |
| POST | /api/run | Upload image, returns `thread_id` |
| GET | /api/stream/{thread_id} | SSE stream |
| POST | /api/hitl/features | Submit reviewed features |
| POST | /api/hitl/grading | Submit reviewed grading |
| POST | /api/hitl/extractions | Submit approved items → `language_items.json` |

## Models

| Role | Model | Provider |
|------|-------|----------|
| Vision | Qwen/Qwen3-VL-8B-Instruct | Together |
| Text (write, grade) | meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8 | Together |
| Language extraction | gpt-4o | OpenAI |

Override text model via `TOGETHER_TEXT_MODEL`. Use OpenAI for text with `USE_TOGETHER_FOR_TEXT=false`.
