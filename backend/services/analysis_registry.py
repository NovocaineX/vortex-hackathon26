from __future__ import annotations
from firebase_config import db

def save_analysis(user_uid: str, analysis_id: str, document_id: str, payload: dict) -> None:
    if db:
        payload["user_uid"] = user_uid
        db.collection("analysis_results").document(analysis_id).set(payload)

def get_analysis(user_uid: str, analysis_id: str) -> dict | None:
    if not db: return None
    ref = db.collection("analysis_results").document(analysis_id).get()
    if ref.exists:
        data = ref.to_dict()
        if data.get("user_uid") == user_uid:
            return data
    return None

def get_latest_analysis_for_document(user_uid: str, document_id: str) -> dict | None:
    if not db: return None
    docs = db.collection("analysis_results").where("user_uid", "==", user_uid).where("document_id", "==", document_id).order_by("created_at", direction="DESCENDING").limit(1).get()
    for d in docs: return d.to_dict()
    return None

def get_all_analyses(user_uid: str) -> list[dict]:
    if not db: return []
    docs = db.collection("analysis_results").where("user_uid", "==", user_uid).order_by("created_at", direction="DESCENDING").get()
    return [d.to_dict() for d in docs]

