from __future__ import annotations

from pathlib import Path

from PIL import Image, ExifTags


def analyze_metadata(file_path: Path, mime_type: str = "") -> dict:
    is_pdf = mime_type == "application/pdf" or file_path.suffix.lower() == ".pdf"
    anomalies: list[dict] = []
    score = 0.0

    if is_pdf:
        pdf_anomalies, pdf_score = _analyze_pdf_metadata(file_path)
        anomalies.extend(pdf_anomalies)
        score = max(score, pdf_score)
    else:
        img_anomalies, img_score = _analyze_image_metadata(file_path)
        anomalies.extend(img_anomalies)
        score = max(score, img_score)

    return {
        "anomalies": anomalies,
        "module_scores": {
            "metadata_integrity": round(score, 3)
        }
    }


def _analyze_pdf_metadata(file_path: Path) -> tuple[list[dict], float]:
    anomalies: list[dict] = []
    score = 0.0
    try:
        import fitz
        doc = fitz.open(str(file_path))
        metadata = doc.metadata or {}
        producer = metadata.get("producer", "").lower()
        creator = metadata.get("creator", "").lower()

        # Check for known manipulative graphics tools
        suspicious_tools = ["photoshop", "gimp", "illustrator", "inkscape", "coreldraw"]
        for tool in suspicious_tools:
            if tool in producer or tool in creator:
                score = max(score, 0.95)
                anomalies.append({
                    "type": "cybersecurity_software_trace",
                    "severity": "HIGH",
                    "confidence": 0.95,
                    "description": f"PDF generated or edited by manipulative image software: {tool.title()}. This strongly suggests document forgery.",
                    "region": None,
                })
        
        doc.close()
    except Exception:
        pass
    
    return anomalies, score


def _analyze_image_metadata(file_path: Path) -> tuple[list[dict], float]:
    anomalies: list[dict] = []
    score = 0.0
    try:
        img = Image.open(file_path)
        exif_data = img._getexif()
        if not exif_data:
            return anomalies, score

        tag_map = {v: k for k, v in ExifTags.TAGS.items()}
        software_tag = tag_map.get("Software")
        dt_orig_tag = tag_map.get("DateTimeOriginal")
        dt_tag = tag_map.get("DateTime")

        if software_tag and software_tag in exif_data:
            sw = str(exif_data[software_tag]).lower()
            edit_keywords = ["photoshop", "gimp", "lightroom", "affinity", "paint", "snapseed", "canva"]
            if any(k in sw for k in edit_keywords):
                score = max(score, 0.95)
                anomalies.append({
                    "type": "cybersecurity_software_trace",
                    "severity": "HIGH",
                    "confidence": 0.95,
                    "description": f"EXIF metadata indicates image was saved using editing software: {sw.title()}. High risk of falsification.",
                    "region": None,
                })

        if dt_orig_tag and dt_tag:
            dt_orig = exif_data.get(dt_orig_tag)
            dt_mod = exif_data.get(dt_tag)
            if dt_orig and dt_mod and str(dt_orig).strip() != str(dt_mod).strip():
                score = max(score, 0.75)
                anomalies.append({
                    "type": "cybersecurity_datetime_mismatch",
                    "severity": "MEDIUM",
                    "confidence": 0.85,
                    "description": "EXIF Original DateTime differs from Modify DateTime, indicating post-capture modification.",
                    "region": None,
                })
    except Exception:
        pass
    
    return anomalies, score
