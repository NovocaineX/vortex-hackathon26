from __future__ import annotations


def calculate_risk_score(module_scores: dict[str, float], anomalies: list[dict]) -> tuple[int, str]:
    weights = {
        "metadata_integrity": 0.25,
        "compression_check": 0.20,
        "pixel_noise": 0.15,
        "edge_artifacts": 0.15,
        "layout_checker": 0.15,
        "ocr_quality": 0.10,
    }
    weighted = 0.0
    weight_sum = 0.0
    for key, weight in weights.items():
        if key in module_scores:
            weighted += module_scores[key] * weight
            weight_sum += weight
    base_score = (weighted / weight_sum) * 100 if weight_sum else 0.0
    severity_bonus = 0
    for item in anomalies:
        sev = item.get("severity", "LOW")
        if sev == "HIGH":
            severity_bonus += 5
        elif sev == "MEDIUM":
            severity_bonus += 2
        else:
            severity_bonus += 0

    score = int(min(100, round(base_score + severity_bonus)))
    return score, classify_risk(score)


def classify_risk(score: int) -> str:
    if score >= 70:
        return "High Risk"
    if score >= 30:
        return "Suspicious"
    return "Low Risk"


def frontend_classification(status: str) -> str:
    if status == "High Risk":
        return "HIGH_RISK"
    if status == "Suspicious":
        return "SUSPICIOUS"
    return "LOW_RISK"
