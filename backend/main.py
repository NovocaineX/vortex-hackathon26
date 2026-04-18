"""
Forensica AI — FastAPI Backend  (main.py)
─────────────────────────────────────────

Entry point.  Run with:
    cd backend
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Interactive API docs:
    http://localhost:8000/api/docs
    http://localhost:8000/api/redoc
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import upload, analyze, results, report

# ── Upload directory ────────────────────────────────────────────────────────
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ── Lifespan (startup / shutdown) ───────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"[Forensica AI] Upload directory: {UPLOAD_DIR.resolve()}")
    print("[Forensica AI] Backend ready. API docs -> http://localhost:8000/api/docs")
    yield
    # Shutdown — optionally clean up temp files
    # for f in UPLOAD_DIR.iterdir():
    #     f.unlink(missing_ok=True)
    print("[Forensica AI] Shutdown complete.")


# ── App factory ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="Forensica AI",
    description=(
        "Document forgery detection REST API. "
        "Provides upload, analysis pipeline, and report endpoints "
        "consumed by the Forensica AI frontend dashboard."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────────────────────
# Allow the frontend dev server (Python http.server on 7823) and any
# Vite/Next dev server to call this API without CORS errors.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:7823",
        "http://127.0.0.1:7823",
        "http://localhost:5173",
        "http://localhost:3000",
        "null",      # file:// origin (when opening index.html directly)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ──────────────────────────────────────────────────────────────────
app.include_router(upload.router,  tags=["Upload"])
app.include_router(analyze.router, tags=["Analysis"])
app.include_router(results.router, tags=["Results"])
app.include_router(report.router,  tags=["Report"])


# ── Health check ────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    """Quick liveness probe used by the frontend status pill."""
    return {
        "status": "ok",
        "service": "Forensica AI",
        "version": "1.0.0",
        "upload_dir": str(UPLOAD_DIR.resolve()),
    }


# ── Dev entry point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
