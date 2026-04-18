"""
utils/aggregator.py
────────────────────
Aggregates per-module scores → overall forgery confidence score,
classification, CSS overlay boxes, and human-readable explanation.
"""

from __future__ import annotations

from models.document import Anomaly, OverlayBox

# ── Score weights ──────────────────────────────────────────────────────────────
_WEIGHTS: dict[str, float] = {
    "font_detector":   0.30,
    "layout_checker":  0.25,
    "pixel_analyzer":  0.35,
    "ocr_extractor":   0.10,
}

_SEV_COLOR = {"HIGH": "red", "MEDIUM": "orange", "LOW": "yellow"}

# ── Classification thresholds ─────────────────────────────────────────────────
_THRESH_HIGH = 62
_THRESH_MED  = 32


def aggregate_score(
    module_scores: dict[str, float],
    anomalies: list[Anomaly],
) -> tuple[int, str]:
    """Return (overall_score_0_100, classification_string)."""
    total, weight_used = 0.0, 0.0
    for key, weight in _WEIGHTS.items():
        if key in module_scores:
            total += module_scores[key] * weight
            weight_used += weight

    base = (total / weight_used * 100) if weight_used > 0 else 0.0

    bump = sum(
        5 if getattr(a, "severity", "") == "HIGH" else
        2 if getattr(a, "severity", "") == "MEDIUM" else 0
        for a in anomalies
    )
    score = int(min(base + bump, 100))

    if score >= _THRESH_HIGH:
        classification = "HIGH_RISK"
    elif score >= _THRESH_MED:
        classification = "SUSPICIOUS"
    else:
        classification = "LOW_RISK"

    return score, classification


def build_overlays(anomalies: list[Anomaly], meta: dict) -> list[OverlayBox]:
    """
    Convert pixel-space AnomalyRegion → CSS percentage OverlayBox.
    One box per anomaly that has a region; deduplicated by (module, anomaly_id).
    """
    img_w = max(meta.get("width", 800) or 800, 1)
    img_h = max(meta.get("height", 1100) or 1100, 1)

    overlays: list[OverlayBox] = []
    seen: set[str] = set()

    for a in sorted(anomalies, key=lambda x: x.severity == "HIGH", reverse=True):
        if a.region is None or a.id in seen:
            continue
        seen.add(a.id)

        x_pct = min(round(a.region.x / img_w * 100, 1), 94)
        y_pct = min(round(a.region.y / img_h * 100, 1), 94)
        w_pct = max(min(round(a.region.w / img_w * 100, 1), 100 - x_pct), 5.0)
        h_pct = max(min(round(a.region.h / img_h * 100, 1), 100 - y_pct), 5.0)

        overlays.append(OverlayBox(
            id=a.id,
            color=_SEV_COLOR.get(a.severity, "yellow"),
            x=f"{x_pct}%", y=f"{y_pct}%",
            w=f"{w_pct}%", h=f"{h_pct}%",
            label=a.label,
        ))

    return overlays


def build_explanation(
    score: int,
    classification: str,
    anomalies: list[Anomaly],
    module_scores: dict[str, float],
    exif_flags: dict,
) -> str:
    """
    Generate a human-readable explanation of the analysis result.
    Draws directly from detected anomalies and scores.
    """
    if not anomalies and score < _THRESH_MED:
        return (
            "No significant anomalies were detected. The document's pixel statistics, "
            "layout structure, and font metrics are consistent with an unmodified document."
        )

    parts: list[str] = []

    # Risk level preamble
    if classification == "HIGH_RISK":
        parts.append(
            f"This document scored {score}/100 on the forgery risk index and is classified "
            "as HIGH RISK. Multiple strong indicators of manipulation were detected."
        )
    elif classification == "SUSPICIOUS":
        parts.append(
            f"This document scored {score}/100 on the forgery risk index and is flagged "
            "as SUSPICIOUS. Moderate anomaly signals require further investigation."
        )
    else:
        parts.append(
            f"This document scored {score}/100 on the forgery risk index. "
            "Low-level anomalies were detected but may be attributable to normal scan/JPEG compression."
        )

    # Anomaly-specific explanations
    high_anoms  = [a for a in anomalies if a.severity == "HIGH"]
    med_anoms   = [a for a in anomalies if a.severity == "MEDIUM"]

    if high_anoms:
        labels = ", ".join(a.label for a in high_anoms)
        parts.append(f"High-confidence findings: {labels}.")

    if med_anoms:
        labels = ", ".join(a.label for a in med_anoms)
        parts.append(f"Moderate findings: {labels}.")

    # Module-specific explanations
    ela_a = next((a for a in anomalies if a.type == "compression_artifact"), None)
    if ela_a:
        parts.append(
            f"Image compression analysis (ELA) identified unusual re-compression signatures "
            f"with {ela_a.confidence:.0%} confidence. "
            "This is consistent with an image that was edited and then re-exported."
        )

    noise_a = next((a for a in anomalies if a.type == "pixel_cloning"), None)
    if noise_a:
        parts.append(
            f"Pixel-noise analysis flagged a region with abnormal variance "
            f"(confidence {noise_a.confidence:.0%}). "
            "Inconsistent noise fingerprints indicate possible cloning or content pasting."
        )

    edge_a = next((a for a in anomalies if a.type == "editing_boundary"), None)
    if edge_a:
        parts.append(
            f"Edge-gradient analysis detected a sharp boundary "
            f"(confidence {edge_a.confidence:.0%}) that is inconsistent with normal "
            "document rendering. This is a common artefact of pasted image regions."
        )

    layout_a = [a for a in anomalies if a.module == "layout_checker"]
    if layout_a:
        la = layout_a[0]
        parts.append(
            f"Layout analysis detected structural irregularities "
            f"(confidence {la.confidence:.0%}): {la.description.split('.')[0]}."
        )

    font_a = [a for a in anomalies if a.module == "font_detector"]
    if font_a:
        fa = font_a[0]
        parts.append(
            f"Typography analysis flagged font inconsistencies "
            f"(confidence {fa.confidence:.0%}). "
            "Text rendered in different styles within a single field is a common forgery indicator."
        )

    # EXIF flags
    if exif_flags.get("software_modified"):
        sw = exif_flags.get("software", "editing software")
        parts.append(
            f"EXIF metadata indicates this image was processed by '{sw}', "
            "which is commonly used for image editing."
        )
    if exif_flags.get("datetime_mismatch"):
        parts.append(
            "EXIF DateTime and DateTimeOriginal fields differ, "
            "suggesting the image was modified after initial capture."
        )

    return " ".join(parts)
