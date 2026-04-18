# Forensica AI

**Explainable Document Forgery Detection Platform**

---

## Project Structure

```
forensica-ai/
│
├── index.html                  ← SPA entry point (served from root)
├── requirements.txt            ← Python backend dependencies
│
├── frontend/
│   ├── css/
│   │   ├── styles.css          ← Design system tokens, layout, components
│   │   └── components.css      ← Animations, modals, responsive breakpoints
│   └── js/
│       ├── app.js              ← Bootstrap entry (type="module")
│       ├── router.js           ← SPA navigation with page lifecycle hooks
│       ├── state.js            ← Centralized application state store
│       ├── api.js              ← API client layer (fetch + mock contracts)
│       ├── upload.js           ← Upload module: drag-drop, validation, pipeline
│       ├── results.js          ← Results panel: anomaly list, overlay rendering
│       ├── report.js           ← Report page: dynamic rendering, download
│       └── utils.js            ← DOM helpers, formatters, toast, animations
│
└── backend/
    ├── main.py                 ← FastAPI app factory + CORS + router mounts
    ├── uploads/                ← Uploaded document storage
    │
    ├── api/
    │   └── routes/
    │       ├── upload.py       ← POST /upload
    │       ├── analyze.py      ← POST /analyze
    │       ├── results.py      ← GET /analysis/{id}
    │       └── report.py       ← GET /report/{id}, GET /report/{id}/download
    │
    ├── models/
    │   └── document.py         ← Pydantic models: DocumentRecord, AnalysisResult, VerificationReport
    │
    ├── services/
    │   ├── upload_service.py   ← File validation, page counting
    │   ├── pipeline_service.py ← Orchestrates all detection modules
    │   ├── ocr_service.py      ← Tesseract OCR text extraction
    │   ├── pixel_analyzer.py   ← OpenCV pixel anomaly & clone detection
    │   ├── layout_checker.py   ← Margin, grid, alignment analysis
    │   ├── font_detector.py    ← Font family & glyph metric comparison
    │   ├── result_store.py     ← In-memory result registry (swap for Redis/DB)
    │   └── report_service.py   ← Builds VerificationReport from results
    │
    └── utils/
        └── aggregator.py       ← Weighted score aggregation & risk classification
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/upload` | Upload document, returns `{id, filename, pages, size_bytes}` |
| `POST` | `/analyze` | Start pipeline, returns `{job_id, status}` |
| `GET`  | `/analysis/{id}` | Poll results: score, classification, anomalies, overlays |
| `GET`  | `/report/{id}` | Fetch structured verification report |
| `GET`  | `/report/{id}/download` | Download PDF report |
| `GET`  | `/health` | System health check |

---

## Running the Application

### Frontend (no build step needed)
```bash
python -m http.server 7823 --directory .
# Visit http://localhost:7823
```

### Backend
```bash
cd backend
pip install -r ../requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# API docs at http://localhost:8000/api/docs
```

### Connect Frontend to Real Backend
In `frontend/js/api.js`, change:
```js
const API_CONFIG = {
  BASE_URL: 'http://localhost:8000',
  MOCK_MODE: false,   // ← switch from true to false
};
```

---

## Detection Pipeline

```
User Upload
    ↓
POST /upload  →  upload_service.py  (validate + store)
    ↓
POST /analyze →  pipeline_service.py (orchestrator)
    ├── ocr_service.py       (Tesseract OCR)
    ├── pixel_analyzer.py    (OpenCV clone/artifact detection)
    ├── layout_checker.py    (margin/grid analysis)
    └── font_detector.py     (font metric comparison)
    ↓
utils/aggregator.py          (weighted scoring → classification)
    ↓
GET /analysis/{id}  →  anomalies, overlays, module scores
GET /report/{id}    →  structured verification report
```

---

## Adding a New Detection Module

1. Create `backend/services/my_module.py` with a `run(document_id) → dict` function
2. Import and call it in `backend/services/pipeline_service.py`
3. Add its weight in `backend/utils/aggregator.py`
4. The API layer and frontend automatically pick up the new module score

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, Vanilla CSS, ES Modules (no build step) |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| OCR | Tesseract via pytesseract |
| Image analysis | OpenCV, NumPy |
| PDF parsing | PyMuPDF (fitz) |
| Report gen | reportlab / weasyprint (optional) |
