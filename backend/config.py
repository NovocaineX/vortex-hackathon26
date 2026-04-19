from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

MAX_UPLOAD_SIZE_BYTES = 15 * 1024 * 1024
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
