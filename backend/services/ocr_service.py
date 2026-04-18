from __future__ import annotations

import numpy as np
from PIL import Image


def extract_text_and_boxes(image: Image.Image) -> dict:
    try:
        import pytesseract
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        full_text = pytesseract.image_to_string(image)

        boxes: list[dict] = []
        for i, text in enumerate(data["text"]):
            text = text.strip()
            conf_raw = data["conf"][i]
            try:
                confidence = max(0.0, min(float(conf_raw) / 100.0, 1.0))
            except ValueError:
                confidence = 0.0
            if not text:
                continue
            boxes.append(
                {
                    "text": text,
                    "x": int(data["left"][i]),
                    "y": int(data["top"][i]),
                    "width": int(data["width"][i]),
                    "height": int(data["height"][i]),
                    "confidence": round(confidence, 3),
                }
            )
        return {"text": full_text.strip(), "boxes": boxes}
    except Exception:
        return _fallback_text_regions(image)


def _fallback_text_regions(image: Image.Image) -> dict:
    gray = np.array(image.convert("L"))
    mask = (gray < 170).astype(np.uint8)
    h, w = mask.shape
    boxes: list[dict] = []
    block_h = max(20, h // 40)
    for y in range(0, h - block_h, block_h):
        row = mask[y : y + block_h, :]
        density = float(row.mean())
        if density < 0.03:
            continue
        xs = np.where(row.sum(axis=0) > 0)[0]
        if len(xs) < 10:
            continue
        x0, x1 = int(xs.min()), int(xs.max())
        boxes.append(
            {
                "text": "",
                "x": x0,
                "y": y,
                "width": max(10, x1 - x0),
                "height": block_h,
                "confidence": round(min(density * 2.5, 1.0), 3),
            }
        )
    return {"text": "", "boxes": boxes}


# ── Real Tesseract OCR ────────────────────────────────────────────────────────
