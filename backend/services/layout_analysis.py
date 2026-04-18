from __future__ import annotations

import statistics


def analyze_layout(ocr_boxes: list[dict], image_w: int, image_h: int) -> dict:
    if len(ocr_boxes) < 2:
        return {"anomalies": [], "regions": [], "module_scores": {"layout_checker": 0.0}}

    boxes = sorted(ocr_boxes, key=lambda b: (b["y"], b["x"]))
    left_edges = [b["x"] for b in boxes]
    centers = [b["x"] + b["width"] / 2 for b in boxes]
    spacings = []
    for i in range(len(boxes) - 1):
        dy = boxes[i + 1]["y"] - boxes[i]["y"]
        if dy > 0:
            spacings.append(dy)

    margin_var = statistics.pstdev(left_edges) if len(left_edges) > 1 else 0.0
    align_var = statistics.pstdev(centers) if len(centers) > 1 else 0.0
    spacing_var = statistics.pstdev(spacings) if len(spacings) > 1 else 0.0

    spacing_score = min(spacing_var / max(image_h * 0.02, 1), 1.0)
    align_score = min(align_var / max(image_w * 0.04, 1), 1.0)
    margin_score = min(margin_var / max(image_w * 0.04, 1), 1.0)
    score = round(max(spacing_score, align_score, margin_score), 3)

    anomalies: list[dict] = []
    regions: list[dict] = []
    if spacing_score > 0.25:
        b = boxes[len(boxes) // 2]
        region = {"x": b["x"], "y": b["y"], "width": b["width"], "height": max(20, b["height"] * 2)}
        anomalies.append(
            {
                "type": "layout_spacing",
                "severity": "MEDIUM",
                "confidence": round(spacing_score, 3),
                "description": "Irregular spacing detected between neighboring text blocks.",
                "region": region,
            }
        )
        regions.append(region)

    if align_score > 0.25:
        b = max(boxes, key=lambda x: abs((x["x"] + x["width"] / 2) - statistics.mean(centers)))
        region = {"x": b["x"], "y": b["y"], "width": b["width"], "height": b["height"]}
        anomalies.append(
            {
                "type": "layout_alignment",
                "severity": "MEDIUM",
                "confidence": round(align_score, 3),
                "description": "Abnormal alignment detected relative to surrounding content.",
                "region": region,
            }
        )
        regions.append(region)

    return {"anomalies": anomalies, "regions": regions, "module_scores": {"layout_checker": score}}
