"""
services/upload_service.py
──────────────────────────
File validation helpers and page counting.
No heavy dependencies — works with stdlib only as baseline.
"""

from __future__ import annotations

import re
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────────
ALLOWED_CONTENT_TYPES: set[str] = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}
# Accepted extensions as fallback when MIME type is missing / wrong
ALLOWED_EXTENSIONS: set[str] = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_SIZE_BYTES: int = 15 * 1024 * 1024   # 15 MB


# ── Validation ────────────────────────────────────────────────────────────────
def validate(content_type: str, filename: str, size_bytes: int) -> dict:
    """
    Validate MIME type (or extension fallback), file extension, and size.
    Returns {"ok": True} or {"ok": False, "error": str}.
    """
    ext = Path(filename).suffix.lower()

    if content_type not in ALLOWED_CONTENT_TYPES and ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        return {
            "ok": False,
            "error": (
                f"Unsupported file type '{content_type}' / extension '{ext}'. "
                f"Allowed: {allowed}."
            ),
        }

    if size_bytes > MAX_SIZE_BYTES:
        mb = size_bytes / 1_048_576
        return {
            "ok": False,
            "error": f"File too large ({mb:.1f} MB). Maximum allowed size is 15 MB.",
        }

    if size_bytes == 0:
        return {"ok": False, "error": "Uploaded file is empty."}

    return {"ok": True}


# ── Safe filename ─────────────────────────────────────────────────────────────
def safe_filename(filename: str) -> str:
    """Strip path separators and restrict to alphanumerics + safe chars."""
    name = Path(filename).name
    name = re.sub(r"[^\w.\-]", "_", name)
    return name or "upload"


# ── Page counting ─────────────────────────────────────────────────────────────
def count_pages(file_path: Path, mime_type: str) -> int:
    """
    Return page count.  Tries PyMuPDF for PDFs; images = 1.
    Gracefully falls back to 1 if PyMuPDF is not installed.
    """
    if mime_type == "application/pdf" or str(file_path).lower().endswith(".pdf"):
        try:
            import fitz  # PyMuPDF — pip install PyMuPDF
            doc = fitz.open(str(file_path))
            return doc.page_count
        except ImportError:
            pass   # PyMuPDF not installed — default to 1
        except Exception:
            pass
    return 1
