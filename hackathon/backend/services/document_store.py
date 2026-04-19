"""
services/document_store.py
─────────────────────────
In-memory registry mapping document_id → DocumentRecord.
This is the single source of truth shared by upload, pipeline, and report routes.

Production replacement: swap _docs dict for a SQLite/PostgreSQL query.
"""

from __future__ import annotations
from pathlib import Path
from models.document import DocumentRecord

# ── Stores ────────────────────────────────────────────────────────────────────
_docs: dict[str, DocumentRecord] = {}


def save(record: DocumentRecord) -> None:
    _docs[record.id] = record


def get(doc_id: str) -> DocumentRecord | None:
    return _docs.get(doc_id)


def all_records() -> list[DocumentRecord]:
    return list(_docs.values())


def delete(doc_id: str) -> None:
    """Remove a document from the registry and delete its stored file."""
    record = _docs.pop(doc_id, None)
    if record and record.file_path:
        path = Path(record.file_path)
        if path.exists():
            path.unlink(missing_ok=True)
