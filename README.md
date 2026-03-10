# JihanBot

Pipeline tạo bài IELTS Writing Task 1 từ ảnh đề bài, dùng LangGraph với Human-in-the-Loop (HITL) và kho cấu trúc ngôn ngữ.

---

## Luồng xử lý (Pipeline)

![Pipeline JihanBot](pipeline-diagram.png)

Luồng: extract question → extract features → **HITL features** → verify extraction → write essay → grade essay → **HITL grading** → extract language units → **HITL extractions** → kết thúc. Ba điểm HITL dừng để người dùng review/sửa trước khi tiếp tục.

---

## Cấu trúc dự án

```
Jihan/
├── pipeline-diagram.png       # Sơ đồ pipeline
├── main.py                    # CLI
├── config.py                  # Cấu hình model (vision, text)
├── requirements.txt          # Dependencies
├── graph/
│   └── workflow.py            # Định nghĩa graph và routing
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
│   └── state.py               # JihanState, ExtractedFeatures, GradingFeedback, ...
├── data/
│   ├── language_taxonomy.json # Phân loại category/subcategory cho language units
│   └── language_items.json    # Kho các cấu trúc đã được user approve
├── utils/
│   └── image.py
└── webapp/                    # Demo giao diện web
    ├── app.py                 # FastAPI (SSE, HITL API)
    ├── requirements.txt
    ├── screenshot.png
    ├── static/
    │   ├── index.html
    │   ├── styles.css
    │   └── app.js
    └── uploads/
```

---

## Chạy CLI

```bash
cd Jihan
pip install -r requirements.txt
```

Copy `.env.example` → `.env` và cấu hình:

- `TOGETHER_API_KEY` – Vision + Text (Together)
- `OPENAI_API_KEY` – Language extraction dùng gpt-4o

```bash
python main.py <đường_dẫn_ảnh> [band_score] [database_path]
```

Ví dụ:

```bash
python main.py ./image.png 7
python main.py ./task1_chart.png 7.5
```

---

## Web Demo

![JihanBot Web Demo](webapp/screenshot.png)

Giao diện web: upload ảnh, xem thinking stream, nhận essay, tham gia HITL tại 3 điểm review, lưu cấu trúc ngôn ngữ vào gallery.

| Khu vực | Mô tả |
|--------|-------|
| **Upload** | Drag & drop ảnh, chọn band 6.0–8.5, nhấn Generate Essay |
| **Thinking** | Log streaming trạng thái theo thời gian thực |
| **Final Essay** | Bài essay sau khi pipeline hoàn tất |
| **Proposed Language Units** | Nút Review → Edit / Approve / Reject từng item → Save Approved |
| **Language Gallery** | Nút Open → Grid cards theo category, filter, Close |

**Thiết kế:** Dark mode (#0f1419, #1e2a3a), accent xanh (#3b82f6). Font: Fraunces, Source Sans 3, JetBrains Mono.

**Chạy:**

```bash
cd Jihan/webapp
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0
```

Mở http://localhost:8000

**API:**

| Method | Path | Mô tả |
|--------|------|-------|
| GET | / | Trang chủ |
| GET | /api/gallery | Lấy items + taxonomy |
| POST | /api/run | Upload ảnh, trả `thread_id` |
| GET | /api/stream/{thread_id} | SSE stream thinking |
| POST | /api/hitl/features | Gửi features đã review |
| POST | /api/hitl/grading | Gửi grading đã review |
| POST | /api/hitl/extractions | Gửi approved items, ghi vào `language_items.json` |

---

## Models

| Vai trò | Model | Provider |
|---------|-------|----------|
| Vision | Qwen/Qwen3-VL-8B-Instruct | Together |
| Text (viết, chấm) | Llama-4-Maverick-17B-128E-Instruct | Together |
| Language extraction | gpt-4o | OpenAI |

Đổi model text qua biến `TOGETHER_TEXT_MODEL`. Dùng OpenAI cho text: `USE_TOGETHER_FOR_TEXT=false`.
