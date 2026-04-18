"""
services/report_service.py
───────────────────────────
Builds VerificationReport from completed analysis results.
Looks up both the DocumentRecord (filename, size) and the
AnalysisResult (anomalies, scores) via their respective stores.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from models.document import (
    VerificationReport,
    ReportVerdict,
    ReportDocumentInfo,
)
from services import document_store, result_store


def build_report(document_id: str) -> VerificationReport | None:
    """
    Construct a VerificationReport for the given document_id.
    Returns None if no completed analysis result exists.
    """
    # ── Look up completed result ──────────────────────────────────────────
    result = _find_result_by_document(document_id)
    if not result:
        return None

    doc = document_store.get(document_id)

    # ── Verdict ───────────────────────────────────────────────────────────
    score          = result.score
    classification = result.classification

    if score >= 65:
        recommendation = (
            "Do not accept this document without manual review by a qualified officer. "
            "Multiple high-confidence anomalies detected."
        )
    elif score >= 35:
        recommendation = (
            "Flag for secondary verification. "
            "Moderate anomaly signals detected — further investigation recommended."
        )
    else:
        recommendation = (
            "Document passed automated screening. "
            "Low forgery risk detected. Standard acceptance procedures may apply."
        )

    # ── Anomaly table rows (flat dicts for JSON serialisation) ────────────
    anomaly_rows = [
        {
            "id":         a.id,
            "type":       a.label,
            "severity":   a.severity,
            "confidence": a.confidence,
            "region": (
                f"({a.region.x},{a.region.y})→({a.region.x + a.region.w},{a.region.y + a.region.h})"
                if a.region else "Global"
            ),
        }
        for a in result.anomalies
    ]

    # ── Module score human labels ─────────────────────────────────────────
    module_label_map = {
        "font_detector":      "Font Inconsistency Detection",
        "layout_checker":     "Layout Consistency Check",
        "pixel_analyzer":     "Pixel Anomaly Detection",
        "ocr_extractor":      "OCR Text Extraction",
        "compression_check":  "Compression Analysis",
    }
    module_scores = {
        module_label_map.get(k, k): round(v, 3)
        for k, v in result.module_scores.items()
    }

    # ── Document info (from store or result) ──────────────────────────────
    if doc:
        doc_info = ReportDocumentInfo(
            filename=doc.filename,
            type=_infer_doc_type(doc.filename, doc.mime_type),
            size_bytes=doc.size_bytes,
            pages=doc.pages,
        )
    else:
        doc_info = ReportDocumentInfo(
            filename="document.pdf",
            type="Unknown",
            size_bytes=0,
            pages=1,
        )

    return VerificationReport(
        report_id="FR-" + uuid.uuid4().hex[:8].upper(),
        document_id=document_id,
        generated_at=datetime.now(timezone.utc),
        verdict=ReportVerdict(
            classification=classification,
            score=score,
            recommendation=recommendation,
        ),
        document_info=doc_info,
        anomalies=anomaly_rows,
        module_scores=module_scores,
        download_url=f"/report/{document_id}/download",
        explanation=result.explanation,
        extracted_text_summary=result.extracted_text[:500] if result.extracted_text else "",
        suspicious_regions=[
            {"x": a.region.x, "y": a.region.y, "w": a.region.w, "h": a.region.h,
             "label": a.label, "severity": a.severity}
            for a in result.anomalies if a.region
        ],
    )


def _find_result_by_document(document_id: str):
    """Scan result_store for a result matching the document_id."""
    from services.result_store import _store
    for result in _store.values():
        if result.document_id == document_id and result.status == "complete":
            return result
    return None


def _infer_doc_type(filename: str, mime_type: str) -> str:
    name = filename.lower()
    if "cert" in name:      return "Academic Certificate"
    if "transcript" in name: return "Academic Transcript"
    if "id" in name:        return "Identity Document"
    if "passport" in name:  return "Passport"
    if mime_type == "application/pdf":  return "PDF Document"
    if "image" in mime_type:            return "Scanned Document"
    return "Document"
