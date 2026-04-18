from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from config import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    MAX_UPLOAD_SIZE_BYTES,
    REPORT_DIR,
)


def sanitize_filename(filename: str) -> str:
    return re.sub(r"[^\w.\-]", "_", Path(filename).name) or "upload"


def is_allowed_upload(content_type: str, filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return content_type in ALLOWED_MIME_TYPES or ext in ALLOWED_EXTENSIONS


def validate_upload(content_type: str, filename: str, size_bytes: int) -> None:
    if not is_allowed_upload(content_type, filename):
        raise ValueError("Unsupported file type. Allowed: PDF, JPG, JPEG, PNG.")
    if size_bytes <= 0:
        raise ValueError("Uploaded file is empty.")
    if size_bytes > MAX_UPLOAD_SIZE_BYTES:
        raise ValueError("File exceeds 15 MB upload limit.")


def new_document_id() -> str:
    return f"doc_{uuid.uuid4().hex[:12]}"


def new_analysis_id() -> str:
    return f"analysis_{uuid.uuid4().hex[:12]}"


def new_report_id() -> str:
    return f"report_{uuid.uuid4().hex[:12]}"


def write_report_json(report_id: str, payload: dict[str, Any]) -> Path:
    report_path = REPORT_DIR / f"{report_id}.json"
    report_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return report_path
