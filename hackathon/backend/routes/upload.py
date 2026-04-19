from __future__ import annotations

import io
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, Depends
from fastapi.responses import Response

from services.document_registry import save_document, get_document
from utils.file_utils import new_document_id, sanitize_filename, validate_upload
from utils.security import get_current_user
from utils.encryption import encrypt_data, decrypt_data
from firebase_config import bucket

router = APIRouter()

# Local fallback storage directory (used when Firebase bucket is absent)
LOCAL_UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), user_info = Depends(get_current_user)) -> dict:
    content = await file.read()
    try:
        validate_upload(file.content_type or "", file.filename or "", len(content))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    uid = user_info.get("uid")
    document_id = new_document_id()
    filename = sanitize_filename(file.filename or "upload")
    
    storage_path = f"secure_uploads/{uid}/{document_id}/encrypted_file"
    encrypted_data = encrypt_data(content)
    
    if bucket:
        blob = bucket.blob(storage_path)
        blob.upload_from_string(encrypted_data, content_type=file.content_type)
    else:
        local_path = LOCAL_UPLOADS_DIR / uid / document_id
        local_path.mkdir(parents=True, exist_ok=True)
        (local_path / "encrypted_file").write_bytes(encrypted_data)
        storage_path = str(local_path / "encrypted_file")

    doc = save_document(
        user_uid=uid,
        document_id=document_id,
        filename=file.filename or filename,
        file_path=storage_path,
        size_bytes=len(content),
        mime_type=file.content_type or "application/octet-stream",
    )
    return {"document_id": document_id, **doc}


@router.get("/preview/{document_id}")
async def preview_document(document_id: str, user_info = Depends(get_current_user)) -> Response:
    """Render page 1 of the uploaded document as JPEG using PyMuPDF."""
    uid = user_info.get("uid")
    record = get_document(uid, document_id)
    if not record:
        raise HTTPException(status_code=404, detail="Document not found")

    storage_path = record.get("file_path")
    mime = record.get("mime_type", "")
    
    raw_bytes = None
    if bucket:
        blob = bucket.blob(storage_path)
        if blob.exists():
            encrypted_bytes = blob.download_as_bytes()
            raw_bytes = decrypt_data(encrypted_bytes)
    else:
        local_file = Path(storage_path)
        if local_file.exists():
            raw_bytes = decrypt_data(local_file.read_bytes())
    
    if not raw_bytes:
        raise HTTPException(status_code=404, detail="File not found in storage")

    # For images, return them directly
    if mime in ("image/jpeg", "image/png") or storage_path.lower().endswith((".jpg", ".jpeg", ".png")):
        return Response(content=raw_bytes, media_type=mime or "image/jpeg")

    # For PDFs, render page 0 via PyMuPDF logic dynamically in memory
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise HTTPException(status_code=501, detail="PyMuPDF not installed")

    try:
        pdf = fitz.open(stream=raw_bytes, filetype="pdf")
        page = pdf[0]
        matrix = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        jpg_bytes = pix.tobytes("jpeg")
        pdf.close()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Render failed: {exc}") from exc

    return Response(content=jpg_bytes, media_type="image/jpeg")

