from __future__ import annotations

_analysis_results: dict[str, dict] = {}
_latest_by_document: dict[str, str] = {}


def save_analysis(analysis_id: str, document_id: str, payload: dict) -> None:
    _analysis_results[analysis_id] = payload
    _latest_by_document[document_id] = analysis_id


def get_analysis(analysis_id: str) -> dict | None:
    return _analysis_results.get(analysis_id)


def get_latest_analysis_for_document(document_id: str) -> dict | None:
    analysis_id = _latest_by_document.get(document_id)
    if not analysis_id:
        return None
    return _analysis_results.get(analysis_id)
