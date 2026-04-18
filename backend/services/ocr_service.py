"""
services/ocr_service.py
────────────────────────
Stage 2: Text extraction and region detection.

Real path: pytesseract (if installed + Tesseract binary present)
Fallback:  Image-based dark-region detection using Pillow+NumPy
           — finds bounding boxes of text-like regions without reading them

The fallback produces real bounding boxes derived from actual image content
(not hardcoded), so layout and font modules receive meaningful region data.
"""

from __future__ import annotations

import io
import math
from pathlib import Path

import numpy as np
from PIL import Image

from models.document import AnomalyRegion


def run(file_path: Path, meta: dict) -> dict:
    """
    Returns:
    {
        "text_blocks": [{"text": str, "zone": [x,y,w,h], "confidence": float}, ...],
        "score":       float,   # OCR anomaly confidence (0-1)
        "language":    str,
        "full_text":   str,     # concatenated extracted text (or summary)
    }
    """
    # Try real Tesseract OCR
    try:
        return _real_ocr(meta)
    except ImportError:
        pass   # pytesseract not installed
    except Exception:
        pass   # Tesseract binary missing or image format unsupported

    # Real image-based text region detection (no reading, but real coordinates)
    return _image_region_detection(meta)


# ── Real Tesseract OCR ────────────────────────────────────────────────────────
def _real_ocr(meta: dict) -> dict:
    import pytesseract

    img: Image.Image = meta["image"]
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

    blocks, low_conf = [], 0
    full_text_parts  = []

    for i, word in enumerate(data["text"]):
        if not word.strip():
            continue
        conf = float(data["conf"][i]) / 100.0
        if conf < 0:
            continue
        if conf < 0.50:
            low_conf += 1
        blocks.append({
            "text":       word,
            "zone":       [data["left"][i], data["top"][i],
                           data["width"][i], data["height"][i]],
            "confidence": round(conf, 3),
        })
        full_text_parts.append(word)

    score = round(low_conf / max(len(blocks), 1), 3)
    return {
        "text_blocks": blocks,
        "score":       score,
        "language":    "en",
        "full_text":   " ".join(full_text_parts),
    }


# ── Image-based region detection (Pillow+NumPy, no Tesseract) ────────────────
def _image_region_detection(meta: dict) -> dict:
    """
    Detect bounding boxes of text-like regions using morphological analysis
    on the pre-computed dark mask. Produces real coordinates from the image.

    Algorithm:
      1. Threshold to binary dark mask
      2. Find connected runs of dark pixels row-by-row (rudimentary CCA)
      3. Merge vertically adjacent runs into text block bounding boxes
      4. Filter by aspect-ratio and size to keep only text-like shapes
    """
    gray: np.ndarray = meta["gray"]    # float32 (H, W).
    w = meta["width"]
    h = meta["height"]

    dark = (gray < 0.45).astype(np.uint8)   # 1 = dark pixel

    # ── Find horizontal runs per row ──────────────────────────────────────
    # Group consecutive dark columns in each row into segments
    segments_per_row: list[list[tuple[int, int]]] = []   # [(x_start, x_end), ...]
    for y in range(h):
        row  = dark[y]
        segs = []
        in_s, s_start = False, 0
        for x, val in enumerate(row):
            if not in_s and val:
                in_s, s_start = True, x
            elif in_s and not val:
                in_s = False
                if x - s_start >= 4:     # min 4px wide
                    segs.append((s_start, x))
        if in_s and w - s_start >= 4:
            segs.append((s_start, w))
        segments_per_row.append(segs)

    # ── Merge rows into blocks ────────────────────────────────────────────
    # A "block" is defined as consecutive rows with overlapping dark segments
    blocks: list[dict] = []
    active: dict | None = None

    for y, segs in enumerate(segments_per_row):
        if not segs:
            if active and y - active["y_end"] > 8:
                blocks.append(active)
                active = None
            continue

        row_left  = min(s[0] for s in segs)
        row_right = max(s[1] for s in segs)

        if active is None:
            active = {"x0": row_left, "x1": row_right,
                      "y0": y, "y_end": y}
        else:
            # Extend active block
            active["x0"]    = min(active["x0"], row_left)
            active["x1"]    = max(active["x1"], row_right)
            active["y_end"] = y

    if active:
        blocks.append(active)

    # ── Filter and convert to zone format ────────────────────────────────
    text_blocks = []
    for blk in blocks:
        bw = blk["x1"] - blk["x0"]
        bh = blk["y_end"] - blk["y0"]

        # Filter: text lines are typically narrow-height but wide
        if bh < 5 or bh > 120:
            continue
        if bw < 20:
            continue

        # Compute dark-pixel density in this block → confidence proxy
        sub   = dark[blk["y0"]:blk["y_end"]+1, blk["x0"]:blk["x1"]+1]
        density = float(sub.mean())
        if density < 0.03:
            continue

        text_blocks.append({
            "text":       "[text region]",     # no OCR here
            "zone":       [blk["x0"], blk["y0"], bw, bh],
            "confidence": round(min(density * 3, 1.0), 3),
        })

    # ── OCR anomaly score: variance of block widths ────────────────────────
    widths = [b["zone"][2] for b in text_blocks]
    if len(widths) >= 3:
        mean_w = sum(widths) / len(widths)
        std_w  = math.sqrt(sum((x - mean_w)**2 for x in widths) / len(widths))
        cv_w   = std_w / (mean_w + 1e-9)
        score  = round(min(cv_w / 1.5, 1.0), 3)
    else:
        score = 0.0

    return {
        "text_blocks": text_blocks,
        "score":       score,
        "language":    "unknown",
        "full_text":   f"[{len(text_blocks)} text regions detected via image analysis]",
    }
