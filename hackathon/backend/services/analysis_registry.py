from __future__ import annotations
from firebase_config import db

LOCAL_RESULTS = {}


def save_analysis(user_uid: str, analysis_id: str, document_id: str, payload: dict) -> None:
    payload["user_uid"] = user_uid
    if db:
        db.collection("analysis_results").document(analysis_id).set(payload)
    else:
        LOCAL_RESULTS[analysis_id] = payload

def get_analysis(user_uid: str, analysis_id: str) -> dict | None:
    if not db:
        data = LOCAL_RESULTS.get(analysis_id)
        if data and dict(data).get("user_uid") == user_uid:
            return data
        return None
        
    ref = db.collection("analysis_results").document(analysis_id).get()
    if ref.exists:
        data = ref.to_dict()
        if data and data.get("user_uid") == user_uid:
            return data
    return None

def get_latest_analysis_for_document(user_uid: str, document_id: str) -> dict | None:
    if not db:
        docs = [d for d in LOCAL_RESULTS.values() if d.get("user_uid") == user_uid and d.get("document_id") == document_id]
        if docs:
            docs.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
            return docs[0]
        return None
        
    docs = db.collection("analysis_results").where("user_uid", "==", user_uid).where("document_id", "==", document_id).order_by("created_at", direction="DESCENDING").limit(1).get()
    for d in docs: return d.to_dict()
    return None

def get_all_analyses(user_uid: str) -> list[dict]:
    if not db:
        docs = [d for d in LOCAL_RESULTS.values() if d.get("user_uid") == user_uid]
        docs.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
        return docs
        
    docs = db.collection("analysis_results").where("user_uid", "==", user_uid).order_by("created_at", direction="DESCENDING").get()
    return [d.to_dict() for d in docs]
