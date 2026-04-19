from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends

from services.analysis_registry import get_analysis, get_latest_analysis_for_document
from services.document_registry import get_document
from utils.file_utils import new_report_id
from utils.security import get_current_user

router = APIRouter()


@router.get("/report/{analysis_id}")
async def get_report(analysis_id: str, user_info = Depends(get_current_user)) -> dict:
    uid = user_info.get("uid")
    result = get_analysis(uid, analysis_id)
    if not result:
        # Frontend may still pass document_id; support that too.
        result = get_latest_analysis_for_document(uid, analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found for report generation.")
    document = get_document(uid, result["document_id"]) or {}

    report_id = new_report_id()
    anomaly_rows = []
    for idx, item in enumerate(result["anomalies"], start=1):
        region = item.get("region")
        region_label = "Global"
        if region:
            region_label = (
                f"({region['x']},{region['y']})→"
                f"({region['x'] + region['width']},{region['y'] + region['height']})"
            )
        anomaly_rows.append(
            {
                "id": f"a{idx}",
                "type": item["type"],
                "severity": item["severity"],
                "confidence": item["confidence"],
                "region": region_label,
            }
        )

    report = {
        "report_id": report_id,
        "analysis_id": result["analysis_id"],
        "document_id": result["document_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "extracted_text_summary": (result.get("extracted_text") or "")[:1200],
        "anomalies": anomaly_rows,
        "suspicious_regions": result["regions"],
        "final_risk_score": result["risk_score"],
        "verdict": {
            "classification": result["classification"],
            "score": result["risk_score"],
            "recommendation": (
                "Do not trust without manual review."
                if result["risk_score"] >= 70
                else "Secondary verification recommended."
                if result["risk_score"] >= 30
                else "Low automated risk."
            ),
        },
        "explanation": result["explanation"],
        "document_info": {
            "filename": document.get("filename", result["document_id"]),
            "size_bytes": document.get("size_bytes", 0),
            "pages": 1,
        },
        "module_scores": result.get("module_scores", {}),
        "download_url": f"/report/{result['analysis_id']}/download",
    }
    return report


@router.get("/report/{analysis_id}/download")
async def download_report_stub(analysis_id: str, user_info = Depends(get_current_user)) -> dict:
    report = await get_report(analysis_id, user_info)
    return {"message": "JSON report generated. PDF export is not configured.", "report": report}
