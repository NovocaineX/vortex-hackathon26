from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from models.analysis_result import AnalyzeRequest
from services.analysis_registry import get_analysis, save_analysis
from services.anomaly_detection import detect_image_anomalies
from services.document_registry import get_document
from services.layout_analysis import analyze_layout
from services.ocr_service import extract_text_and_boxes
from services.preprocessing import load_document_images
from services.risk_scoring import calculate_risk_score, frontend_classification
from utils.file_utils import new_analysis_id
from utils.image_utils import dedupe_regions, to_overlay

router = APIRouter()


@router.post("/analyze")
async def analyze_document(payload: AnalyzeRequest) -> dict:
    document = get_document(payload.document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Invalid document_id.")

    file_path = Path(document["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Uploaded file is missing on disk.")

    try:
        pages = load_document_images(file_path)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    anomalies: list[dict] = []
    all_regions: list[dict] = []
    module_scores: dict[str, float] = {}
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

    final_regions = dedupe_regions(all_regions + [{"x": b["x"], "y": b["y"], "width": b["width"], "height": b["height"]} for b in ocr_boxes[:15]])
    overlays = [
        to_overlay(region, pages[0].size[0], pages[0].size[1], "red", "Suspicious Region")
        for region in final_regions[:20]
    ]

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
    save_analysis(analysis_id, payload.document_id, result)
    return {"analysis_id": analysis_id, "job_id": analysis_id, "status": "complete"}


@router.get("/analysis/{analysis_id}")
async def get_analysis_result(analysis_id: str) -> dict:
    result = get_analysis(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Invalid analysis_id.")
    return result
