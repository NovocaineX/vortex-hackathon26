"""
services/file_preprocessor.py
──────────────────────────────
Stage 1: File preprocessing using Pillow + NumPy.

Converts the uploaded document into a normalised RGB PIL Image that all
downstream modules share. Also extracts basic structural metadata and EXIF
anomaly flags.

Returns a rich `meta` dict consumed by every subsequent module:
{
    width, height, channels, file_hash,
    is_pdf, page_count, file_size,
    image: PIL.Image (RGB, normalised),
    array: np.ndarray (H, W, 3) uint8,
    gray:  np.ndarray (H, W) float32 [0..1],
    exif_flags: {has_exif, software_modified, gps_present, ...}
}
"""

from __future__ import annotations

import hashlib
import io
import struct
from pathlib import Path


def process(file_path: Path, mime_type: str) -> dict:
    """
    Load and normalise the document into a shared meta dict.
    All downstream analysis modules receive this dict so they
    don't each re-open the file independently.
    """
    import numpy as np
    from PIL import Image, ExifTags

    raw       = file_path.read_bytes()
    file_hash = hashlib.sha256(raw).hexdigest()
    is_pdf    = mime_type == "application/pdf" or file_path.suffix.lower() == ".pdf"
    page_count = 1

    # ── Load image into PIL ──────────────────────────────────────────────
    if is_pdf:
        img, page_count = _load_pdf_as_image(file_path, raw)
    else:
        img = Image.open(io.BytesIO(raw))

    # Normalise: always RGB, cap at 2400px on the long edge (processing limit)
    img = img.convert("RGB")
    img = _cap_resolution(img, max_long_edge=2400)

    w, h    = img.size
    arr     = np.asarray(img, dtype=np.uint8)
    gray    = np.mean(arr.astype(np.float32) / 255.0, axis=2)   # [0..1]

    # ── EXIF flags ────────────────────────────────────────────────────────
    exif_flags = _extract_exif_flags(img, is_pdf)

    return {
        "width":      w,
        "height":     h,
        "channels":   3,
        "file_hash":  file_hash,
        "is_pdf":     is_pdf,
        "page_count": page_count,
        "file_size":  len(raw),
        "image":      img,        # PIL Image (RGB)
        "array":      arr,        # NumPy uint8 (H,W,3)
        "gray":       gray,       # NumPy float32 (H,W)
        "exif_flags": exif_flags,
    }


# ── PDF rasterisation ─────────────────────────────────────────────────────────
def _load_pdf_as_image(file_path: Path, raw: bytes):
    """Rasterise first page of PDF at 150 dpi → PIL Image."""
    try:
        import fitz   # PyMuPDF
        doc  = fitz.open(str(file_path))
        mat  = fitz.Matrix(150 / 72, 150 / 72)   # 150 dpi
        pix  = doc[0].get_pixmap(matrix=mat, alpha=False)
        img  = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img, doc.page_count
    except ImportError:
        pass

    # Fallback: white A4 canvas when PyMuPDF not installed
    from PIL import Image as PILImage
    img = PILImage.new("RGB", (1240, 1754), "white")
    return img, 1


# ── Resolution cap ────────────────────────────────────────────────────────────
def _cap_resolution(img, max_long_edge: int):
    from PIL import Image
    w, h   = img.size
    long_e = max(w, h)
    if long_e > max_long_edge:
        scale = max_long_edge / long_e
        img   = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return img


# ── EXIF extraction ───────────────────────────────────────────────────────────
def _extract_exif_flags(img, is_pdf: bool) -> dict:
    flags = {
        "has_exif":          False,
        "software_modified": False,
        "software":          None,
        "gps_present":       False,
        "datetime_mismatch": False,
    }
    if is_pdf:
        return flags
    try:
        from PIL import ExifTags
        exif_data = img._getexif()
        if not exif_data:
            return flags

        flags["has_exif"] = True
        tag_map   = {v: k for k, v in ExifTags.TAGS.items()}

        software_tag  = tag_map.get("Software")
        gps_tag       = tag_map.get("GPSInfo")
        dt_orig_tag   = tag_map.get("DateTimeOriginal")
        dt_tag        = tag_map.get("DateTime")

        if software_tag and software_tag in exif_data:
            sw = str(exif_data[software_tag])
            flags["software"] = sw
            # Common editing tools
            edit_keywords = ["photoshop", "gimp", "lightroom", "affinity", "paint"]
            if any(k in sw.lower() for k in edit_keywords):
                flags["software_modified"] = True

        if gps_tag and gps_tag in exif_data:
            flags["gps_present"] = True

        if dt_orig_tag and dt_tag:
            dt_orig = exif_data.get(dt_orig_tag)
            dt_mod  = exif_data.get(dt_tag)
            if dt_orig and dt_mod and dt_orig != dt_mod:
                flags["datetime_mismatch"] = True
    except Exception:
        pass

    return flags
