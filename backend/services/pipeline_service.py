"""
services/pipeline_service.py
─────────────────────────────
Orchestrates the full forgery detection pipeline.

Runs as a FastAPI BackgroundTask. Stages:
  1. file_preprocessor  — load image into PIL/NumPy, extract EXIF
  2. ocr_service        — text region detection (Tesseract or image-based)
  3. pixel_analyzer     — ELA, block-noise, edge gradient (Pillow+NumPy)
  4. layout_checker     — margin variance, spacing, blob detection
  5. font_detector      — line-height CoV, stroke width (or PDF font names)
  6. aggregator         — weighted score + classification + explanation
  7. result_store.save  — persist for GET /analysis/{id}
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from models.document import AnalysisJob, AnalysisResult, Anomaly, OverlayBox
from services import (
    document_store,
    job_store,
    result_store,
    ocr_service,
    pixel_analyzer,
    layout_checker,
    font_detector,
    file_preprocessor,
)
from utils.aggregator import aggregate_score, build_overlays, build_explanation


async def run_pipeline(job: AnalysisJob) -> None:
    """
    Full async pipeline. Updates job_store at each stage.
    All exceptions are caught so the job is marked 'error' on failure.
    """
    job.status = "running"
    job_store.save(job)

    try:
        # ── Resolve uploaded file ─────────────────────────────────────────
        doc = document_store.get(job.document_id)
        if not doc or not doc.file_path:
            raise FileNotFoundError(f"No file registered for document {job.document_id}")
        file_path = Path(doc.file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Stored file missing: {file_path}")

        # ── Stage 1: Preprocessing ────────────────────────────────────────
        meta = file_preprocessor.process(file_path, doc.mime_type)
        await asyncio.sleep(0)

        # ── Stage 2: OCR / Text region detection ──────────────────────────
        ocr_result = ocr_service.run(file_path, meta)
        await asyncio.sleep(0)

        # ── Stage 3: Pixel analysis ───────────────────────────────────────
        pixel_result = pixel_analyzer.run(file_path, meta)
        await asyncio.sleep(0)

        # ── Stage 4: Layout analysis ──────────────────────────────────────
        layout_result = layout_checker.run(file_path, meta)
        await asyncio.sleep(0)

        # ── Stage 5: Font analysis ────────────────────────────────────────
        font_result = font_detector.run(file_path, meta)
        await asyncio.sleep(0)

        # ── Stage 6: Aggregate ────────────────────────────────────────────
        all_anomalies: list[Anomaly] = (
            pixel_result["anomalies"]
            + layout_result["anomalies"]
            + font_result["anomalies"]
        )

        module_scores: dict[str, float] = {
            "ocr_extractor":     ocr_result["score"],
            "pixel_analyzer":    pixel_result["score"],
            "layout_checker":    layout_result["score"],
            "font_detector":     font_result["score"],
            "compression_check": pixel_result.get("compression_score", 0.0),
        }

        overall_score, classification = aggregate_score(module_scores, all_anomalies)
        overlays = build_overlays(all_anomalies, meta)

        exif_flags = meta.get("exif_flags", {})
        explanation = build_explanation(
            overall_score, classification, all_anomalies, module_scores, exif_flags
        )

        # Text region list for report page (raw pixel coords)
        text_regions = [
            {"x": b["zone"][0], "y": b["zone"][1],
             "w": b["zone"][2], "h": b["zone"][3],
             "confidence": b["confidence"]}
            for b in ocr_result.get("text_blocks", [])
        ]

        result = AnalysisResult(
            job_id=job.job_id,
            document_id=job.document_id,
            status="complete",
            score=overall_score,
            classification=classification,
            anomalies=all_anomalies,
            overlays=overlays,
            module_scores=module_scores,
            completed_at=datetime.now(timezone.utc),
            explanation=explanation,
            extracted_text=ocr_result.get("full_text", ""),
            text_regions=text_regions,
        )
        result_store.save(job.job_id, result)

        job.status = "complete"
        job.completed_at = datetime.now(timezone.utc)

    except Exception:
        job.status = "error"
        import traceback
        traceback.print_exc()

    finally:
        job_store.save(job)
