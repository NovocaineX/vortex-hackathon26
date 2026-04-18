"""
api/routes/results.py
─────────────────────
GET /analysis/{job_id}

Returns the full analysis result payload once the pipeline is complete.
While running, returns a 202 with current status so the frontend can
continue polling.

Response shape matches the frontend api.js mock contract exactly:
{
  job_id, document_id, status, score, classification,
  anomalies[], overlays[], module_scores{}, completed_at
}
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from models.document import AnalysisResult
from services import job_store, result_store

router = APIRouter()


@router.get("/analysis/{job_id}", response_model=AnalysisResult)
async def get_analysis_results(job_id: str, response: Response):
    """
    Return full analysis results for a completed job.

    - 200  job complete   → full AnalysisResult payload
    - 202  still running  → {status, message}  (not 404, keeps client polling)
    - 404  job not found
    """
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    if job.status == "error":
        raise HTTPException(status_code=500, detail="Analysis pipeline failed.")

    result = result_store.get(job_id)
    if result:
        return result

    # Still processing — return 202 so the client keeps polling
    response.status_code = 202
    # We can't return AnalysisResult here (incomplete), so return raw dict
    return {
        "job_id": job_id,
        "document_id": job.document_id,
        "status": job.status,
        "score": None,
        "classification": None,
        "anomalies": [],
        "overlays": [],
        "module_scores": {},
        "completed_at": None,
    }
