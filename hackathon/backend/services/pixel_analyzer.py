"""
services/pixel_analyzer.py
───────────────────────────
Stage 3: Real pixel-level anomaly detection using Pillow + NumPy only.
No OpenCV required.

Techniques implemented:
  1. Error Level Analysis (ELA) — JPEG re-compression delta via Pillow
  2. Block noise variance     — 32px block std-dev grid via NumPy
  3. Edge gradient analysis   — Sobel-like gradient for paste boundaries

All three run directly on the PIL Image cached in `meta["image"]`.
"""

from __future__ import annotations

import io
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from models.document import Anomaly, AnomalyRegion

_BLOCK = 32          # Block size for variance grid


def run(file_path: Path, meta: dict) -> dict:
    """
    Run all three pixel analysis passes on the pre-loaded image.
    Returns structured anomalies + module scores.
    """
    img: Image.Image = meta["image"]       # PIL RGB already normalised
    arr: np.ndarray  = meta["array"]       # uint8 (H, W, 3)
    gray: np.ndarray = meta["gray"]        # float32 (H, W), range 0-1

    w, h = img.size
    anomalies: list[Anomaly] = []

    ela_score,   ela_anomalies   = _ela_analysis(img, file_path)
    noise_score, noise_anomalies = _block_noise_analysis(gray, w, h)
    edge_score,  edge_anomalies  = _edge_analysis(arr, gray, w, h)

    anomalies = ela_anomalies + noise_anomalies + edge_anomalies

    pixel_score      = max(ela_score, noise_score, edge_score)
    compression_score = ela_score

    return {
        "anomalies":          anomalies,
        "score":              round(pixel_score, 3),
        "compression_score":  round(compression_score, 3),
        "heatmap_data":       None,
    }


# ── 1. Error Level Analysis (ELA) ────────────────────────────────────────────
def _ela_analysis(img: Image.Image, file_path: Path) -> tuple[float, list[Anomaly]]:
    """
    Resave the image at JPEG quality 90 in memory, compute per-pixel absolute
    difference.  High residuals indicate regions that were modified and then
    re-compressed, a classic sign of image manipulation.

    Meaningful for all formats (not just JPEG): even PNG documents that were
    edited and then screenshotted/exported show characteristic ELA patterns.
    """
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    recompressed = Image.open(buf).convert("RGB")

    orig = np.asarray(img, dtype=np.float32)
    recp = np.asarray(recompressed, dtype=np.float32)
    ela  = np.abs(orig - recp)          # shape (H, W, 3)
    ela_gray = ela.mean(axis=2)         # (H, W)

    global_mean = float(ela_gray.mean())
    global_std  = float(ela_gray.std())

    # ELA score: normalised mean residual (0-1)
    # Pristine images score ~0.01-0.08; edited ones score >0.15
    ela_score = min(global_mean / 15.0, 1.0)

    anomalies: list[Anomaly] = []

    # Only flag if residual is meaningfully above noise floor
    if global_mean > 5.0:
        threshold = global_mean + 2.5 * global_std

        # Find the 32×32 block with the highest ELA residual
        H, W = ela_gray.shape
        best_bx, best_by, best_v = 0, 0, 0.0
        for by in range(0, H - _BLOCK, _BLOCK):
            for bx in range(0, W - _BLOCK, _BLOCK):
                v = float(ela_gray[by:by+_BLOCK, bx:bx+_BLOCK].mean())
                if v > best_v:
                    best_v, best_bx, best_by = v, bx, by

        if best_v > threshold:
            conf = min(best_v / 30.0, 0.95)
            sev  = "HIGH" if conf > 0.65 else "MEDIUM" if conf > 0.40 else "LOW"
            anomalies.append(Anomaly(
                id="px_ela",
                type="compression_artifact",
                label="Compression Artifact",
                severity=sev,
                confidence=round(conf, 3),
                description=(
                    f"Error Level Analysis detected re-compression residual of "
                    f"{global_mean:.1f} (threshold {5.0:.1f}). "
                    f"Highest-anomaly block at pixel ({best_bx},{best_by}). "
                    "This pattern is consistent with image editing followed by re-export."
                ),
                region=AnomalyRegion(x=best_bx, y=best_by, w=_BLOCK * 4, h=_BLOCK * 4),
                module="pixel_analyzer",
            ))

    return ela_score, anomalies


# ── 2. Block Noise Variance ───────────────────────────────────────────────────
def _block_noise_analysis(gray: np.ndarray, w: int, h: int) -> tuple[float, list[Anomaly]]:
    """
    Divide the image into 32px blocks and compute per-block std deviation.
    Blocks with variance far above the image mean indicate editing artefacts,
    noise injection, or pasted regions (which have different noise fingerprints).
    """
    variances: list[tuple[int, int, float]] = []

    for by in range(0, h - _BLOCK, _BLOCK):
        for bx in range(0, w - _BLOCK, _BLOCK):
            tile = gray[by:by+_BLOCK, bx:bx+_BLOCK]
            variances.append((bx, by, float(np.std(tile))))

    if not variances:
        return 0.0, []

    vals     = [v for _, _, v in variances]
    mean_std = sum(vals) / len(vals)
    sd_std   = math.sqrt(sum((v - mean_std)**2 for v in vals) / len(vals)) + 1e-9
    threshold = mean_std + 2.8 * sd_std

    suspicious = [(bx, by, v) for bx, by, v in variances if v > threshold]
    if not suspicious:
        return 0.0, []

    hv_bx, hv_by, hv_v = max(suspicious, key=lambda t: t[2])
    conf  = min((hv_v - mean_std) / (sd_std * 4), 1.0)
    score = round(conf, 3)

    if conf < 0.25:
        return score, []

    sev = "HIGH" if conf > 0.70 else "MEDIUM" if conf > 0.45 else "LOW"
    anomaly = Anomaly(
        id="px_noise",
        type="pixel_cloning",
        label="Noise Inconsistency",
        severity=sev,
        confidence=score,
        description=(
            f"Block noise variance at ({hv_bx},{hv_by}) is {hv_v:.4f} vs "
            f"image mean {mean_std:.4f}. "
            f"{len(suspicious)} region(s) exceeded the {sd_std:.4f} std-dev threshold. "
            "Inconsistent noise patterns indicate possible cloning or pasting."
        ),
        region=AnomalyRegion(x=hv_bx, y=hv_by, w=_BLOCK * 3, h=_BLOCK * 3),
        module="pixel_analyzer",
    )
    return score, [anomaly]


# ── 3. Edge / Paste Boundary Detection ───────────────────────────────────────
def _edge_analysis(arr: np.ndarray, gray: np.ndarray, w: int, h: int) -> tuple[float, list[Anomaly]]:
    """
    Compute a Sobel-like gradient magnitude via NumPy and look for
    unnaturally sharp linear boundaries. Pasted regions often have a
    hard rectangular edge that doesn't match the surrounding texture.
    """
    # Sobel kernels via convolution on grayscale
    gy = np.gradient(gray, axis=0)
    gx = np.gradient(gray, axis=1)
    magnitude = np.sqrt(gx**2 + gy**2)   # (H, W)

    # Check row-wise and column-wise mean gradient for sharp horizontal/vertical lines
    row_means = magnitude.mean(axis=1)    # (H,)
    col_means = magnitude.mean(axis=0)    # (W,)

    row_mean = float(row_means.mean())
    col_mean = float(col_means.mean())
    row_std  = float(row_means.std()) + 1e-9
    col_std  = float(col_means.std()) + 1e-9

    # Find the sharpest row and column
    sharpest_row     = int(np.argmax(row_means))
    sharpest_row_val = float(row_means[sharpest_row])
    sharpest_col     = int(np.argmax(col_means))
    sharpest_col_val = float(col_means[sharpest_col])

    row_z = (sharpest_row_val - row_mean) / row_std
    col_z = (sharpest_col_val - col_mean) / col_std
    max_z = max(row_z, col_z)

    edge_score = min(max_z / 8.0, 1.0)

    # Only flag clear statistical outliers (z-score > 3.5)
    if max_z < 3.5 or edge_score < 0.20:
        return edge_score, []

    is_row_dominant = row_z >= col_z
    conf = round(min(max_z / 10.0, 0.95), 3)
    sev  = "HIGH" if conf > 0.70 else "MEDIUM"

    if is_row_dominant:
        region = AnomalyRegion(x=0, y=max(0, sharpest_row - _BLOCK), w=w, h=_BLOCK * 2)
        desc = (
            f"Sharp horizontal edge detected at row {sharpest_row} "
            f"(z-score {row_z:.1f}). Gradient magnitude is {sharpest_row_val:.4f} vs "
            f"mean {row_mean:.4f}. This boundary is consistent with a pasted image region."
        )
    else:
        region = AnomalyRegion(x=max(0, sharpest_col - _BLOCK), y=0, w=_BLOCK * 2, h=h)
        desc = (
            f"Sharp vertical edge detected at column {sharpest_col} "
            f"(z-score {col_z:.1f}). Gradient magnitude is {sharpest_col_val:.4f} vs "
            f"mean {col_mean:.4f}. Possible pasted or overlaid region boundary."
        )

    return edge_score, [Anomaly(
        id="px_edge",
        type="editing_boundary",
        label="Sharp Edit Boundary",
        severity=sev,
        confidence=conf,
        description=desc,
        region=region,
        module="pixel_analyzer",
    )]
