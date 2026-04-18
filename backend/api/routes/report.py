"""
api/routes/report.py
────────────────────
GET  /report/{document_id}           → structured verification report
GET  /report/{document_id}/download  → PDF download (stub until reportlab wired)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from models.document import VerificationReport
from services import document_store, report_service

router = APIRouter()


@router.get("/report/{document_id}", response_model=VerificationReport)
async def get_report(document_id: str):
    """
    Build and return the structured verification report for a document.
    Requires that analysis has been completed (result must be in result_store).

    Response shape matches frontend api.js mock contract:
    {
      report_id, document_id, generated_at, verdict{},
      document_info{}, anomalies[], module_scores{}, download_url
    }
    """
    doc = document_store.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    report = report_service.build_report(document_id)
    if not report:
        raise HTTPException(
            status_code=404,
            detail="No completed analysis found for this document. Run POST /analyze first.",
        )
    return report


@router.get("/report/{document_id}/download")
async def download_report(document_id: str):
    """
    Download PDF version of the report.
    Returns report data as JSON until PDF generation (reportlab) is wired up.
    """
    doc = document_store.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    report = report_service.build_report(document_id)
    if not report:
        raise HTTPException(status_code=404, detail="No completed analysis found.")

    return {
        "message": "PDF generation pending backend reportlab integration.",
        "report": report.model_dump(),
    }
