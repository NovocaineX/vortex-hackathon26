from __future__ import annotations

import io

import numpy as np
from PIL import Image

from utils.image_utils import clamp_box


def detect_image_anomalies(image: Image.Image) -> dict:
    array = np.array(image.convert("RGB"))
    gray = array.mean(axis=2).astype(np.float32)
    h, w = gray.shape

    ela_regions, ela_score = _error_level_analysis(image, w, h)
    noise_regions, noise_score = _noise_analysis(gray, w, h)
    edge_regions, edge_score = _edge_artifact_analysis(gray, w, h)

    anomalies: list[dict] = []
    for region in ela_regions:
        anomalies.append(
            {
                "type": "compression_artifact",
                "severity": "HIGH" if ela_score > 0.6 else "MEDIUM",
                "confidence": round(ela_score, 3),
                "description": "Compression inconsistencies detected in highlighted region indicating potential image editing.",
                "region": region,
            }
        )
    for region in noise_regions:
        anomalies.append(
            {
                "type": "noise_inconsistency",
                "severity": "MEDIUM" if noise_score > 0.35 else "LOW",
                "confidence": round(noise_score, 3),
                "description": "Inconsistent noise profile detected compared to surrounding document texture.",
                "region": region,
            }
        )
    for region in edge_regions:
        anomalies.append(
            {
                "type": "edge_artifact",
                "severity": "MEDIUM" if edge_score > 0.35 else "LOW",
                "confidence": round(edge_score, 3),
                "description": "Sharp boundary artifact suggests potential pasted or edited region.",
                "region": region,
            }
        )

    return {
        "anomalies": anomalies,
        "regions": ela_regions + noise_regions + edge_regions,
        "module_scores": {
            "compression_check": round(ela_score, 3),
            "pixel_noise": round(noise_score, 3),
            "edge_artifacts": round(edge_score, 3),
        },
    }


def _error_level_analysis(image: Image.Image, w: int, h: int) -> tuple[list[dict], float]:
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    recompressed = Image.open(buf).convert("RGB")
    diff = np.abs(np.array(image, dtype=np.float32) - np.array(recompressed, dtype=np.float32)).mean(axis=2)

    threshold = float(diff.mean() + 2.5 * diff.std())
    block = 64
    candidates: list[tuple[float, int, int]] = []
    for y in range(0, h - block, block):
        for x in range(0, w - block, block):
            score = float(diff[y : y + block, x : x + block].mean())
            if score > threshold:
                candidates.append((score, x, y))
    candidates.sort(reverse=True)
    regions = [clamp_box(x, y, block * 2, block * 2, w, h) for _, x, y in candidates[:3]]
    ela_score = min(float(diff.mean()) / 15.0, 1.0)
    return regions, ela_score


def _noise_analysis(gray: np.ndarray, w: int, h: int) -> tuple[list[dict], float]:
    block = 32
    values: list[tuple[float, int, int]] = []
    for y in range(0, h - block, block):
        for x in range(0, w - block, block):
            std = float(gray[y : y + block, x : x + block].std())
            values.append((std, x, y))
    if not values:
        return [], 0.0
    means = [v[0] for v in values]
    mean_std = float(np.mean(means))
    std_std = float(np.std(means)) + 1e-6
    outliers = [(v, x, y) for v, x, y in values if v > mean_std + (2.0 * std_std)]
    outliers.sort(reverse=True)
    regions = [clamp_box(x, y, block * 3, block * 3, w, h) for _, x, y in outliers[:3]]
    score = min((max([o[0] for o in outliers], default=mean_std) - mean_std) / (4 * std_std), 1.0)
    return regions, float(max(score, 0.0))


def _edge_artifact_analysis(gray: np.ndarray, w: int, h: int) -> tuple[list[dict], float]:
    gx = np.gradient(gray, axis=1)
    gy = np.gradient(gray, axis=0)
    mag = np.sqrt(gx**2 + gy**2)
    row_means = mag.mean(axis=1)
    col_means = mag.mean(axis=0)
    row_idx = int(np.argmax(row_means))
    col_idx = int(np.argmax(col_means))
    row_z = (float(row_means[row_idx]) - float(row_means.mean())) / (float(row_means.std()) + 1e-6)
    col_z = (float(col_means[col_idx]) - float(col_means.mean())) / (float(col_means.std()) + 1e-6)
    score = min(max(row_z, col_z) / 8.0, 1.0)
    regions: list[dict] = []
    if row_z > 3.0:
        regions.append(clamp_box(0, row_idx - 20, w, 40, w, h))
    if col_z > 3.0:
        regions.append(clamp_box(col_idx - 20, 0, 40, h, w, h))
    return regions, float(max(score, 0.0))
