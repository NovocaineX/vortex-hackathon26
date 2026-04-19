"""
models/document.py — Pydantic data models for documents and analysis jobs
"""

from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class DocumentRecord(BaseModel):
    id: str
    filename: str
    size_bytes: int
    pages: int
    mime_type: str
    uploaded_at: datetime
    file_path: Optional[str] = None


class AnalysisJob(BaseModel):
    job_id: str
    document_id: str
    user_uid: str
    status: str           # queued | running | complete | error
    created_at: datetime
    completed_at: Optional[datetime] = None


class AnomalyRegion(BaseModel):
    x: int
    y: int
    w: int
    h: int


class Anomaly(BaseModel):
    id: str
    type: str
    label: str
    severity: str         # HIGH | MEDIUM | LOW
    confidence: float
    description: str
    region: Optional[AnomalyRegion] = None
    module: str           # which detector flagged this


class OverlayBox(BaseModel):
    id: str
    color: str            # red | orange | yellow
    x: str               # CSS percentage string  e.g. "55%"
    y: str
    w: str
    h: str
    label: str


class AnalysisResult(BaseModel):
    job_id: str
    document_id: str
    status: str
    score: int                           # 0–100 forgery confidence
    classification: str                  # LOW_RISK | SUSPICIOUS | HIGH_RISK
    anomalies: List[Anomaly]
    overlays: List[OverlayBox]
    module_scores: Dict[str, float]
    completed_at: Optional[datetime] = None
    # ── Explanation engine output (added for enhanced analysis) ──────────
    explanation: str = ""                # human-readable summary
    extracted_text: str = ""            # OCR / text summary
    text_regions: List[Dict] = []       # raw text bounding boxes


class ReportVerdict(BaseModel):
    classification: str
    score: int
    recommendation: str


class ReportDocumentInfo(BaseModel):
    filename: str
    type: str
    size_bytes: int
    pages: int


class VerificationReport(BaseModel):
    report_id: str
    document_id: str
    generated_at: datetime
    verdict: ReportVerdict
    document_info: ReportDocumentInfo
    anomalies: List[dict]
    module_scores: Dict[str, float]
    download_url: str
    # ── Enhanced report fields ─────────────────────────────────────────────
    explanation: str = ""
    extracted_text_summary: str = ""
    suspicious_regions: List[Dict] = []  # raw pixel-space regions for report page
