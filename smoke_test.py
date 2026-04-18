from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageDraw

BASE_URL = "http://localhost:8000"


def build_sample_image() -> bytes:
    image = Image.new("RGB", (900, 1200), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 40, 860, 180), outline="black", width=3)
    draw.text((70, 90), "FORENSICA SAMPLE CERTIFICATE", fill="black")
    draw.rectangle((520, 420, 820, 620), fill=(210, 210, 210), outline="black", width=2)
    draw.text((80, 300), "Name: Jane Doe", fill="black")
    draw.text((80, 360), "ID: 24A-2026", fill="black")
    draw.text((80, 980), "Issuer Signature", fill="black")
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def main() -> None:
    print("=== Forensica backend smoke test ===")
    health = requests.get(f"{BASE_URL}/health", timeout=8).json()
    print("health:", health)

    sample = build_sample_image()
    files = {"file": ("sample_document.png", sample, "image/png")}
    upload = requests.post(f"{BASE_URL}/upload", files=files, timeout=20).json()
    print("upload:", json.dumps(upload, indent=2))

    analyze = requests.post(
        f"{BASE_URL}/analyze",
        json={"document_id": upload["document_id"]},
        timeout=90,
    ).json()
    print("analyze:", json.dumps(analyze, indent=2))

    analysis = requests.get(f"{BASE_URL}/analysis/{analyze['analysis_id']}", timeout=30).json()
    print("analysis:", json.dumps(analysis, indent=2))

    report = requests.get(f"{BASE_URL}/report/{analyze['analysis_id']}", timeout=30).json()
    print("report:", json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
