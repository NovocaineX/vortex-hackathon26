"""
services/job_store.py
─────────────────────
Shared in-memory job registry.

Importing from a single module keeps the dict truly shared across
all route modules (avoids the "each module gets its own dict" problem
that happens when _jobs is defined inside a route file).

Production replacement: Redis / Celery task state.
"""

from __future__ import annotations
from models.document import AnalysisJob

_jobs: dict[str, AnalysisJob] = {}


def save(job: AnalysisJob) -> None:
    _jobs[job.job_id] = job


def get(job_id: str) -> AnalysisJob | None:
    return _jobs.get(job_id)


def update_status(job_id: str, status: str) -> None:
    job = _jobs.get(job_id)
    if job:
        job.status = status
        _jobs[job_id] = job


def all_jobs() -> list[AnalysisJob]:
    return list(_jobs.values())
