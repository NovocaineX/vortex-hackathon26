from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Region(BaseModel):
    x: int
    y: int
    width: int
    height: int


class Anomaly(BaseModel):
    type: str
    severity: str
    confidence: float
    description: str
    region: Region | None = None


class AnalyzeRequest(BaseModel):
    document_id: str


class AnalyzeResponse(BaseModel):
    analysis_id: str
    job_id: str
    status: str


class AnalysisResultResponse(BaseModel):
    analysis_id: str
    document_id: str
    risk_score: int
    score: int
    status: str
    classification: str
    anomalies: list[dict[str, Any]]
    regions: list[Region]
    overlays: list[dict[str, str]]
    explanation: str
    module_scores: dict[str, float]
    extracted_text: str = ""
    completed_at: datetime


class ReportResponse(BaseModel):
    report_id: str
    analysis_id: str
    document_id: str
    generated_at: datetime
    extracted_text_summary: str
    anomalies: list[dict[str, Any]]
    suspicious_regions: list[Region]
    final_risk_score: int
    verdict: dict[str, Any] = Field(default_factory=dict)
    explanation: str
