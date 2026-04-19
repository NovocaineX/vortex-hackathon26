"""
services/layout_checker.py
───────────────────────────
Stage 4: Real layout consistency analysis using Pillow + NumPy.

Detects structural document layout anomalies without needing OCR:

  1. Text-row detection  — horizontal dark-pixel runs → text line positions
  2. Margin variance     — left / right margin consistency per text row
  3. Line-spacing gaps   — abnormal inter-row spacing ratios
  4. Block isolation     — large isolated dark blobs in unexpected positions
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image

from models.document import Anomaly, AnomalyRegion


def run(file_path: Path, meta: dict) -> dict:
    gray: np.ndarray = meta["gray"]    # float32 (H, W) [0..1]
    w    = meta["width"]
    h    = meta["height"]

    anomalies: list[Anomaly] = []
    score = 0.0

    row_data = _find_text_rows(gray, w, h)
    if len(row_data) >= 3:
        margin_score, margin_anomaly  = _margin_variance(row_data, w, h)
        spacing_score, spacing_anomaly = _line_spacing(row_data, h)

        for a in (margin_anomaly, spacing_anomaly):
            if a:
                anomalies.append(a)

        score = max(margin_score, spacing_score)

    # Additional: detect isolated large dark blobs outside text rows
    blob_score, blob_anomaly = _isolated_blob(gray, w, h, row_data)
    if blob_anomaly:
        anomalies.append(blob_anomaly)
    score = max(score, blob_score)

    return {"anomalies": anomalies, "score": round(score, 3)}


# ── Text-row detection ────────────────────────────────────────────────────────
def _find_text_rows(gray: np.ndarray, w: int, h: int) -> list[dict]:
    """
    A "text row" is a horizontal band where dark pixels (< 0.4 brightness)
    appear on more than 8% of the row width.
    Returns list of {y, left_edge, right_edge, density}.
    """
    dark_mask = (gray < 0.4).astype(np.float32)   # 1 where dark
    row_density = dark_mask.mean(axis=1)           # fraction dark per row

    threshold = max(0.04, float(row_density.mean()) * 1.5)
    rows = []
    for y, density in enumerate(row_density):
        if density > threshold:
            row_pixels = dark_mask[y]
            nz = np.nonzero(row_pixels)[0]
            if len(nz) > 5:
                rows.append({
                    "y":          int(y),
                    "left_edge":  int(nz[0]),
                    "right_edge": int(nz[-1]),
                    "density":    float(density),
                })
    return rows


# ── Margin variance analysis ──────────────────────────────────────────────────
def _margin_variance(row_data: list[dict], w: int, h: int) -> tuple[float, Anomaly | None]:
    """
    Compute std-dev of left and right edges across text rows.
    High variance = inconsistent margins = possible tampering.
    """
    lefts  = [r["left_edge"]  for r in row_data]
    rights = [r["right_edge"] for r in row_data]

    mean_left = sum(lefts) / len(lefts)
    std_left  = math.sqrt(sum((l - mean_left)**2 for l in lefts) / len(lefts))

    mean_right = sum(rights) / len(rights)
    std_right  = math.sqrt(sum((r - mean_right)**2 for r in rights) / len(rights))

    # Normalise: > 30px std is suspicious for a well-formatted document
    margin_score = min((std_left + std_right) / 2 / 60.0, 1.0)

    if margin_score < 0.25:
        return margin_score, None

    # Worst outlier row for the bounding box
    outlier = max(row_data, key=lambda r: abs(r["left_edge"] - mean_left))
    conf = round(margin_score, 3)
    sev  = "HIGH" if conf > 0.65 else "MEDIUM"

    return margin_score, Anomaly(
        id="lay_margin",
        type="layout_irregularity",
        label="Margin Inconsistency",
        severity=sev,
        confidence=conf,
        description=(
            f"Left-margin std-dev is {std_left:.1f}px across {len(row_data)} text rows "
            f"(mean {mean_left:.1f}px). Right-margin std-dev is {std_right:.1f}px. "
            "Inconsistent margins are characteristic of text block insertion or removal."
        ),
        region=AnomalyRegion(
            x=max(0, int(mean_left) - 30),
            y=max(0, outlier["y"] - 10),
            w=min(int(w * 0.60), w),
            h=60,
        ),
        module="layout_checker",
    )


# ── Line spacing analysis ─────────────────────────────────────────────────────
def _line_spacing(row_data: list[dict], h: int) -> tuple[float, Anomaly | None]:
    """
    Compute gaps between successive text rows. Abnormally large or small gaps
    break the expected rhythm of a standard document.
    """
    if len(row_data) < 4:
        return 0.0, None

    # Collapse adjacent rows into lines (gap < 5px = same line)
    lines = [row_data[0]]
    for r in row_data[1:]:
        if r["y"] - lines[-1]["y"] > 5:
            lines.append(r)

    gaps = [lines[i+1]["y"] - lines[i]["y"] for i in range(len(lines) - 1)]
    if not gaps:
        return 0.0, None

    mean_gap = sum(gaps) / len(gaps)
    std_gap  = math.sqrt(sum((g - mean_gap)**2 for g in gaps) / len(gaps)) + 1e-9

    # z-score of the largest gap
    max_gap   = max(gaps)
    max_idx   = gaps.index(max_gap)
    z_score   = (max_gap - mean_gap) / std_gap
    score     = min(z_score / 8.0, 1.0)

    if z_score < 3.0 or score < 0.20:
        return score, None

    conf = round(min(z_score / 10.0, 0.95), 3)
    sev  = "HIGH" if conf > 0.65 else "MEDIUM"

    gap_y = lines[max_idx]["y"]
    return score, Anomaly(
        id="lay_spacing",
        type="layout_irregularity",
        label="Line Spacing Anomaly",
        severity=sev,
        confidence=conf,
        description=(
            f"Abnormal gap of {max_gap}px detected at row {gap_y} "
            f"(z-score {z_score:.1f}; mean gap {mean_gap:.1f}px ± {std_gap:.1f}px). "
            "Irregular spacing is consistent with text block deletion or insertion."
        ),
        region=AnomalyRegion(
            x=0, y=max(0, gap_y - 20),
            w=lines[max_idx].get("right_edge", 600),
            h=max_gap + 40,
        ),
        module="layout_checker",
    )


# ── Isolated dark blob detection ──────────────────────────────────────────────
def _isolated_blob(
    gray: np.ndarray, w: int, h: int, text_rows: list[dict]
) -> tuple[float, Anomaly | None]:
    """
    Find large dark-pixel clusters that don't align with any detected text row.
    A pasted seal, stamp, or image block will appear as an isolated dense blob.
    """
    text_y_set = {r["y"] for r in text_rows}

    # Divide into 64px blocks; flag blocks with high dark density not near text rows
    block = 64
    candidates = []

    dark_mask = (gray < 0.35).astype(np.float32)
    for by in range(0, h - block, block):
        # Skip if any text row is within 20px of this block
        near_text = any(abs(by - ty) < 20 for ty in text_y_set)
        if near_text:
            continue
        for bx in range(0, w - block, block):
            density = float(dark_mask[by:by+block, bx:bx+block].mean())
            if density > 0.12:    # >12% dark pixels: meaningful blob
                candidates.append((bx, by, density))

    if not candidates:
        return 0.0, None

    # Best candidate
    bx, by, density = max(candidates, key=lambda t: t[2])
    conf  = min(density / 0.35, 1.0)
    score = round(conf, 3)

    if conf < 0.30:
        return score, None

    sev = "MEDIUM" if conf < 0.65 else "HIGH"
    return score, Anomaly(
        id="lay_blob",
        type="isolated_region",
        label="Isolated Dark Region",
        severity=sev,
        confidence=score,
        description=(
            f"Isolated dark region detected at ({bx},{by}) with pixel density {density:.2%}. "
            "This region does not align with detected text rows and may represent "
            "a pasted image, stamp, or seal inserted independently of the document."
        ),
        region=AnomalyRegion(x=bx, y=by, w=block * 2, h=block * 2),
        module="layout_checker",
    )
