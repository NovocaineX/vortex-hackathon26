from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from firebase_config import db

def save_document(user_uid: str, document_id: str, filename: str, file_path: str, size_bytes: int, mime_type: str) -> dict:
    payload = {
        "document_id": document_id,
        "user_uid": user_uid,
        "filename": filename,
        "file_path": file_path,
        "size_bytes": size_bytes,
        "mime_type": mime_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "queued"
    }
    if db:
        db.collection("documents").document(document_id).set(payload)
    return payload

def get_document(user_uid: str, document_id: str) -> dict | None:
    if not db:
        return None
    doc_ref = db.collection("documents").document(document_id).get()
    if doc_ref.exists:
        data = doc_ref.to_dict()
        if data.get("user_uid") == user_uid:
            return data
    return None

def get_documents_by_user(user_uid: str) -> list[dict]:
    if not db:
        return []
    docs = db.collection("documents").where("user_uid", "==", user_uid).order_by("created_at", direction="DESCENDING").get()
    return [doc.to_dict() for doc in docs]

