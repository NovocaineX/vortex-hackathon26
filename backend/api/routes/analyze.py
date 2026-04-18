"""
api/routes/analyze.py
─────────────────────
POST /analyze

Validates that the document exists, creates a job entry, and kicks off
the detection pipeline as a background task.

GET /analyze/{job_id}/status  (lightweight poll)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from models.document import AnalysisJob
from services import job_store, document_store, pipeline_service

router = APIRouter()


class AnalyzeRequest(BaseModel):
    document_id: str


@router.post("/analyze", response_model=AnalysisJob, status_code=202)
async def start_analysis(body: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Trigger the forgery detection pipeline for a previously uploaded document.

    Returns a job object immediately (status: queued).
    Poll GET /analysis/{job_id} for results.
    """
    # Ensure the document actually exists
    doc = document_store.get(body.document_id)
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{body.document_id}' not found. Upload it first via POST /upload.",
        )

    job = AnalysisJob(
        job_id="job_" + uuid.uuid4().hex[:10],
        document_id=body.document_id,
        status="queued",
        created_at=datetime.now(timezone.utc),
    )
    job_store.save(job)

    background_tasks.add_task(pipeline_service.run_pipeline, job)

    return job


@router.get("/analyze/{job_id}/status", response_model=AnalysisJob)
async def get_job_status(job_id: str):
    """Lightweight status poll — returns job state without full result payload."""
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
