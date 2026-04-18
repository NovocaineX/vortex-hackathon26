"""
services/result_store.py
─────────────────────────
Shared in-memory analysis result registry.
Accessed by pipeline_service (write), results route (read), and report_service (scan).

Production replacement: Redis HSET / PostgreSQL results table.
"""

from __future__ import annotations
from models.document import AnalysisResult

_store: dict[str, AnalysisResult] = {}


def save(job_id: str, result: AnalysisResult) -> None:
    _store[job_id] = result


def get(job_id: str) -> AnalysisResult | None:
    return _store.get(job_id)


def all_results() -> list[AnalysisResult]:
    return list(_store.values())


def delete(job_id: str) -> None:
    _store.pop(job_id, None)
