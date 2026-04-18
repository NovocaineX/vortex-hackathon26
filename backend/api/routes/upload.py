"""
api/routes/upload.py
────────────────────
POST /upload

Accepts a document (PDF / JPG / PNG), validates type and size,
persists it to disk, registers it in the document store, and
returns structured metadata the frontend can use as the document_id
for subsequent /analyze calls.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from models.document import DocumentRecord
from services import document_store, upload_service

router = APIRouter()

# Resolve uploads/ relative to the backend package root
_BACKEND_ROOT = Path(__file__).parent.parent.parent   # → backend/
UPLOAD_DIR = _BACKEND_ROOT / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", response_model=DocumentRecord, status_code=201)
async def upload_document(file: UploadFile = File(...)):
    """
    Accept a document file, validate it, store it, and return doc metadata.

    Response shape (matches frontend api.js mock contract):
        { id, filename, pages, size_bytes, mime_type, uploaded_at, file_path }
    """
    # ── Read full content first (so we can check size) ────────────────────
    contents = await file.read()

    # ── Validate ──────────────────────────────────────────────────────────
    validation = upload_service.validate(
        content_type=file.content_type or "",
        filename=file.filename or "",
        size_bytes=len(contents),
    )
    if not validation["ok"]:
        raise HTTPException(status_code=422, detail=validation["error"])

    # ── Persist ───────────────────────────────────────────────────────────
    doc_id    = "doc_" + uuid.uuid4().hex[:10]
    safe_name = upload_service.safe_filename(file.filename or "upload")
    save_path = UPLOAD_DIR / f"{doc_id}_{safe_name}"
    save_path.write_bytes(contents)

    # ── Page count (best-effort; falls back to 1) ─────────────────────────
    pages = upload_service.count_pages(save_path, file.content_type or "")

    record = DocumentRecord(
        id=doc_id,
        filename=file.filename or safe_name,
        size_bytes=len(contents),
        pages=pages,
        mime_type=file.content_type or "application/octet-stream",
        uploaded_at=datetime.now(timezone.utc),
        file_path=str(save_path),
    )
    document_store.save(record)
    return record
