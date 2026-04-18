from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from config import UPLOAD_DIR
from services.document_registry import save_document
from utils.file_utils import new_document_id, sanitize_filename, validate_upload

router = APIRouter()


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)) -> dict:
    content = await file.read()
    try:
        validate_upload(file.content_type or "", file.filename or "", len(content))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    document_id = new_document_id()
    filename = sanitize_filename(file.filename or "upload")
    target = UPLOAD_DIR / f"{document_id}_{filename}"
    target.write_bytes(content)

    doc = save_document(
        document_id=document_id,
        filename=file.filename or filename,
        file_path=Path(target),
        size_bytes=len(content),
        mime_type=file.content_type or "application/octet-stream",
    )
    return {"document_id": document_id, **doc}
