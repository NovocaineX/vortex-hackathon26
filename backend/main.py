from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import REPORT_DIR, UPLOAD_DIR
from routes import analysis, report, upload


# ── Lifespan (startup / shutdown) ───────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[Forensica AI] Upload directory: {UPLOAD_DIR.resolve()}")
    print(f"[Forensica AI] Report directory: {REPORT_DIR.resolve()}")
    yield
    print("[Forensica AI] Shutdown complete")


# ── App factory ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="Forensica AI",
    description="Document forgery detection API using OCR + image analysis + layout checks.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:7823",
        "http://127.0.0.1:7823",
        "http://localhost:5173",
        "http://localhost:3000",
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router,  tags=["Upload"])
app.include_router(analysis.router, tags=["Analysis"])
app.include_router(report.router,  tags=["Report"])


# ── Health check ────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "ok",
        "service": "Forensica AI",
        "version": "1.0.0",
        "upload_dir": str(UPLOAD_DIR.resolve()),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
