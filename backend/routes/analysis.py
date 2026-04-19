from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends

from models.analysis_result import AnalyzeRequest
from services.analysis_registry import get_analysis, save_analysis
from services.anomaly_detection import detect_image_anomalies
from services.document_registry import get_document, get_documents_by_user
from utils.security import get_current_user
from services.layout_analysis import analyze_layout
from services.metadata_forensics import analyze_metadata
from services.ocr_service import extract_text_and_boxes
from services.preprocessing import load_document_images
from services.risk_scoring import calculate_risk_score, frontend_classification
from utils.file_utils import new_analysis_id
from utils.image_utils import dedupe_regions, to_overlay
from utils.encryption import decrypt_data

router = APIRouter()


@router.post("/analyze")
async def analyze_document(payload: AnalyzeRequest, user_info = Depends(get_current_user)) -> dict:
    uid = user_info.get("uid")
    document = get_document(uid, payload.document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Invalid document_id.")

    from firebase_config import bucket
    
    file_path = document["file_path"]
    raw_bytes = None
    if bucket:
        blob = bucket.blob(file_path)
        if blob.exists():
            encrypted_bytes = blob.download_as_bytes()
            raw_bytes = decrypt_data(encrypted_bytes)
            
    if not raw_bytes:
        raise HTTPException(status_code=404, detail="Uploaded file is missing on storage.")

    try:
        pages = load_document_images(raw_bytes, document.get("mime_type", ""))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    metadata_result = analyze_metadata(raw_bytes)

    anomalies: list[dict] = []
    anomalies.extend(metadata_result["anomalies"])
    all_regions: list[dict] = []
    module_scores: dict[str, float] = {}
    module_scores.update(metadata_result["module_scores"])
    full_text_parts: list[str] = []
    ocr_boxes: list[dict] = []

    for page in pages:
        page_w, page_h = page.size
        try:
            ocr = extract_text_and_boxes(page)
            image_anomaly = detect_image_anomalies(page)
            layout_anomaly = analyze_layout(ocr["boxes"], page_w, page_h)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed processing document: {exc}") from exc

        full_text_parts.append(ocr["text"])
        ocr_boxes.extend(ocr["boxes"])

        anomalies.extend(image_anomaly["anomalies"])
        anomalies.extend(layout_anomaly["anomalies"])
        all_regions.extend(image_anomaly["regions"])
        all_regions.extend(layout_anomaly["regions"])

        module_scores.update(image_anomaly["module_scores"])
        module_scores.update(layout_anomaly["module_scores"])

        avg_conf = sum(b["confidence"] for b in ocr["boxes"]) / max(1, len(ocr["boxes"]))
        module_scores["ocr_quality"] = max(module_scores.get("ocr_quality", 0.0), 1 - avg_conf)

    risk_score, status = calculate_risk_score(module_scores, anomalies)
    classification = frontend_classification(status)
    analysis_id = new_analysis_id()

    final_regions = []
    overlays = []
    seen_regions = set()
    for anomaly in anomalies:
        region = anomaly.get("region")
        if not region:
            continue
        # Use tuples for deduplication
        key = (region.get("x"), region.get("y"), region.get("width"), region.get("height"))
        if key in seen_regions:
            continue
        seen_regions.add(key)
        
        final_regions.append(region)
        label = anomaly.get("type", "Anomaly").replace("_", " ").title()
        
        # Determine color based on severity
        sev = anomaly.get("severity", "LOW")
        color = "red" if sev == "HIGH" else ("orange" if sev == "MEDIUM" else "yellow")
        
        overlays.append(
            to_overlay(region, pages[0].size[0], pages[0].size[1], color, label)
        )

    explanation = (
        "Document analysis completed using OCR, compression artifact checks, noise profiling, "
        "edge artifact detection, and layout consistency analysis."
    )
    if anomalies:
        explanation += f" {len(anomalies)} anomaly signal(s) were detected across the uploaded document."
    else:
        explanation += " No strong anomaly signal was detected."

    result = {
        "analysis_id": analysis_id,
        "job_id": analysis_id,
        "document_id": payload.document_id,
        "risk_score": risk_score,
        "score": risk_score,
        "status": status,
        "classification": classification,
        "anomalies": anomalies,
        "regions": final_regions,
        "overlays": overlays,
        "module_scores": module_scores,
        "explanation": explanation,
        "extracted_text": "\n".join(p for p in full_text_parts if p).strip(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    save_analysis(uid, analysis_id, payload.document_id, result)
    return {"analysis_id": analysis_id, "job_id": analysis_id, "status": "complete"}


@router.get("/analysis/{analysis_id}")
async def get_analysis_result(analysis_id: str, user_info = Depends(get_current_user)) -> dict:
    uid = user_info.get("uid")
    result = get_analysis(uid, analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Invalid analysis_id.")
    return result

@router.get("/documents")
async def get_document_history(user_info = Depends(get_current_user)) -> dict:
    uid = user_info.get("uid")
    docs = get_documents_by_user(uid)
    return {"documents": docs}
