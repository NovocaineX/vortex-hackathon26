from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

_documents: dict[str, dict] = {}


def save_document(document_id: str, filename: str, file_path: Path, size_bytes: int, mime_type: str) -> dict:
    payload = {
        "id": document_id,
        "filename": filename,
        "file_path": str(file_path),
        "size_bytes": size_bytes,
        "mime_type": mime_type,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    _documents[document_id] = payload
    return payload


def get_document(document_id: str) -> dict | None:
    return _documents.get(document_id)
