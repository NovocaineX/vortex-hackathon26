from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from firebase_config import db

LOCAL_DB = {}


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
    else:
        LOCAL_DB[document_id] = payload
    return payload

def get_document(user_uid: str, document_id: str) -> dict | None:
    if not db:
        data = LOCAL_DB.get(document_id)
        if data and data.get("user_uid") == user_uid:
            return data
        return None
        
    doc_ref = db.collection("documents").document(document_id).get()
    if doc_ref.exists:
        data = doc_ref.to_dict()
        if data.get("user_uid") == user_uid:
            return data
    return None

def get_documents_by_user(user_uid: str) -> list[dict]:
    if not db:
        docs = [d for d in LOCAL_DB.values() if d.get("user_uid") == user_uid]
        docs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return docs
        
    docs = db.collection("documents").where("user_uid", "==", user_uid).order_by("created_at", direction="DESCENDING").get()
    return [doc.to_dict() for doc in docs]

