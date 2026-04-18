from __future__ import annotations

from pathlib import Path

from PIL import Image


def load_document_images(file_path: Path) -> list[Image.Image]:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return _pdf_to_images(file_path)

    image = Image.open(file_path).convert("RGB")
    return [_normalize_resolution(image)]


def _pdf_to_images(file_path: Path) -> list[Image.Image]:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PDF processing requires PyMuPDF (`pip install pymupdf`).") from exc

    doc = fitz.open(str(file_path))
    pages: list[Image.Image] = []
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages.append(_normalize_resolution(img))
    doc.close()
    return pages or [Image.new("RGB", (1200, 1600), "white")]


def _normalize_resolution(image: Image.Image, max_side: int = 2000) -> Image.Image:
    image = image.convert("RGB")
    width, height = image.size
    long_side = max(width, height)
    if long_side <= max_side:
        return image
    scale = max_side / long_side
    return image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
