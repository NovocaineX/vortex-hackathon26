from __future__ import annotations
from models.document import AnalysisResult
from firebase_config import db

LOCAL_RESULTS = {}


def save(user_uid: str, job_id: str, result: AnalysisResult) -> None:
    payload = result.dict()
    payload["user_uid"] = user_uid
    if db:
        db.collection("analysis_results").document(job_id).set(payload)
    else:
        LOCAL_RESULTS[job_id] = payload

def get(user_uid: str, job_id: str) -> dict | None:
    if not db:
        data = LOCAL_RESULTS.get(job_id)
        if data and data.get("user_uid") == user_uid:
            return data
        return None
        
    ref = db.collection("analysis_results").document(job_id).get()
    if ref.exists:
        data = ref.to_dict()
        if data.get("user_uid") == user_uid:
            return data
    return None

def delete(user_uid: str, job_id: str) -> None:
    if db:
        ref = db.collection("analysis_results").document(job_id).get()
        if ref.exists and ref.to_dict().get("user_uid") == user_uid:
            db.collection("analysis_results").document(job_id).delete()
    else:
        if job_id in LOCAL_RESULTS and LOCAL_RESULTS[job_id].get("user_uid") == user_uid:
            del LOCAL_RESULTS[job_id]

