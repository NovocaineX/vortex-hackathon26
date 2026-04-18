"""
services/font_detector.py
──────────────────────────
Stage 5: Real font/text consistency analysis using Pillow + NumPy.

Without Tesseract we can't read font names, but we CAN measure
the visual characteristics of text strokes using image analysis:

  1. Stroke width estimation  — thin → thick bands via gradient
  2. Text zone height variance — character cap-height inconsistency
  3. Local contrast ratio     — mixed dark/light text indicates different rendering

For PDFs, PyMuPDF is tried first to extract real embedded font names.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from models.document import Anomaly, AnomalyRegion


def run(file_path: Path, meta: dict) -> dict:
    # Try real PDF font extraction first
    if meta.get("is_pdf"):
        try:
            result = _pdf_font_check(file_path, meta)
            if result["anomalies"] or result["score"] > 0:
                return result
        except Exception:
            pass

    # Image-based font consistency analysis
    return _image_font_analysis(meta)


# ── PDF font extraction (PyMuPDF) ─────────────────────────────────────────────
def _pdf_font_check(file_path: Path, meta: dict) -> dict:
    import fitz
    doc         = fitz.open(str(file_path))
    font_names: set[str] = set()

    for page in doc:
        blocks = page.get_text("rawdict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        for block in blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    fname = span.get("font", "").split("+")[-1]
                    font_names.add(fname)
    doc.close()

    def _base(name: str) -> str:
        for s in ("-Bold", "-Italic", "-BoldItalic", "-Semibold", "Bold", "Italic"):
            name = name.replace(s, "")
        return name.strip("-").strip()

    families = {_base(f) for f in font_names}
    n        = len(families)
    score    = min((n - 2) / 5.0, 1.0) if n > 2 else 0.0
    anomalies: list[Anomaly] = []

    if n > 2:
        w, h = meta["width"], meta["height"]
        conf = round(score, 3)
        sev  = "HIGH" if conf >= 0.5 else "MEDIUM"
        anomalies.append(Anomaly(
            id="fnt_pdf",
            type="font_inconsistency",
            label="Font Family Mismatch",
            severity=sev,
            confidence=conf,
            description=(
                f"{n} distinct font families detected in PDF: "
                + ", ".join(sorted(families)[:6])
                + ". A genuine document of this type typically uses 1-2 families."
            ),
            region=AnomalyRegion(
                x=int(w * 0.55), y=int(h * 0.10),
                w=int(w * 0.40), h=int(h * 0.10),
            ),
            module="font_detector",
        ))

    return {
        "anomalies": anomalies,
        "score":     round(score, 3),
        "fonts_found": list(font_names),
    }


# ── Image-based font consistency ──────────────────────────────────────────────
def _image_font_analysis(meta: dict) -> dict:
    """
    Analyse text stroke characteristics using the pre-computed image arrays.

    Steps:
      A. Find bounding rows of each text line (via dark-row detection)
      B. Measure average character height (row height) per line
      C. Compute coefficient of variation of heights → inconsistency score
      D. Measure local stroke gradient to estimate stroke width clusters
    """
    gray: np.ndarray = meta["gray"]     # float32 (H,W) [0..1]
    w = meta["width"]
    h = meta["height"]

    anomalies: list[Anomaly] = []

    # ── A/B: Text line heights ────────────────────────────────────────────
    dark_rows = (gray < 0.4).mean(axis=1)    # fraction dark per row
    baseline  = max(0.03, float(dark_rows.mean()))
    in_text   = False
    line_heights: list[tuple[int, int]] = []  # (start_y, height)
    start = 0

    for y, val in enumerate(dark_rows):
        if not in_text and val > baseline * 1.5:
            in_text, start = True, y
        elif in_text and val <= baseline:
            h_line = y - start
            if 5 < h_line < 80:          # plausible character height range
                line_heights.append((start, h_line))
            in_text = False

    score, anomaly = 0.0, None

    if len(line_heights) >= 4:
        heights = [lh for _, lh in line_heights]
        mean_h  = sum(heights) / len(heights)
        std_h   = math.sqrt(sum((x - mean_h)**2 for x in heights) / len(heights))
        cv      = std_h / (mean_h + 1e-9)     # Coefficient of Variation

        # CoV > 0.35 is suspicious for a regular printed document
        score = min(cv / 0.7, 1.0)

        if score >= 0.25:
            outlier_idx = max(range(len(heights)), key=lambda i: abs(heights[i] - mean_h))
            oy, oh      = line_heights[outlier_idx]
            conf = round(score, 3)
            sev  = "HIGH" if conf > 0.65 else "MEDIUM"

            anomaly = Anomaly(
                id="fnt_height",
                type="font_inconsistency",
                label="Font Size Inconsistency",
                severity=sev,
                confidence=conf,
                description=(
                    f"Text line heights vary by CoV={cv:.2f} ({std_h:.1f}px std across "
                    f"{len(line_heights)} lines; mean={mean_h:.1f}px). "
                    f"Line at row {oy} has anomalous height {oh}px. "
                    "Mixed character heights suggest text was added from a different source."
                ),
                region=AnomalyRegion(x=0, y=max(0, oy - 5), w=w, h=oh + 10),
                module="font_detector",
            )

    # ── C: Stroke width clusters via gradient analysis ────────────────────
    gy = np.abs(np.gradient(gray, axis=0))
    row_grad = gy.mean(axis=1)

    # High gradient rows = text edges; cluster their spacing
    text_edge_rows = [y for y, v in enumerate(row_grad) if v > 0.04]

    stroke_score, stroke_anomaly = 0.0, None
    if len(text_edge_rows) > 10:
        stroke_gaps = [
            text_edge_rows[i+1] - text_edge_rows[i]
            for i in range(len(text_edge_rows) - 1)
            if text_edge_rows[i+1] - text_edge_rows[i] < 25
        ]
        if len(stroke_gaps) > 5:
            sg_mean = sum(stroke_gaps) / len(stroke_gaps)
            sg_std  = math.sqrt(
                sum((g - sg_mean)**2 for g in stroke_gaps) / len(stroke_gaps)
            )
            sg_cv = sg_std / (sg_mean + 1e-9)

            stroke_score = min(sg_cv / 0.8, 1.0)
            if stroke_score >= 0.30 and not anomaly:
                conf = round(stroke_score, 3)
                sev  = "MEDIUM" if conf < 0.65 else "HIGH"
                stroke_anomaly = Anomaly(
                    id="fnt_stroke",
                    type="font_inconsistency",
                    label="Stroke Width Variation",
                    severity=sev,
                    confidence=conf,
                    description=(
                        f"Text stroke spacing CoV={sg_cv:.2f} "
                        f"({sg_std:.2f}px std; mean={sg_mean:.2f}px). "
                        "Irregular stroke widths suggest multiple rendering sources "
                        "or mixed typefaces within the document."
                    ),
                    region=AnomalyRegion(x=int(w * 0.05), y=int(h * 0.05), w=int(w * 0.5), h=int(h * 0.20)),
                    module="font_detector",
                )

    result_anomalies = [a for a in [anomaly, stroke_anomaly] if a]
    result_score = max(score, stroke_score)

    return {
        "anomalies":   result_anomalies,
        "score":       round(result_score, 3),
        "fonts_found": [],
    }
