from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import analysis, report, upload, auth
import firebase_config  # Initializes Firebase on app start


# ── Lifespan (startup / shutdown) ───────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Forensica AI] Started securely with Firebase.")
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,    tags=["Authentication"])
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
        "storage": "Firebase",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
