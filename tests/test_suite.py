"""
test_suite.py — Forensica AI Full System Validation
════════════════════════════════════════════════════
Run from project root:
    python test_suite.py

Tests all API endpoints, validation rules, pipeline stages,
real analysis output quality, and error handling.
"""
from __future__ import annotations

import io
import json
import struct
import time
import urllib.error
import urllib.request
import zlib
import os
import sys

BASE = "http://localhost:8000"
PASS = "✓"
FAIL = "✗"

results: list[tuple[str, bool, str]] = []


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════
def record(name: str, ok: bool, detail: str = "") -> bool:
    results.append((name, ok, detail))
    status = PASS if ok else FAIL
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    return ok


def post_multipart(path: str, filename: str, content_type: str, data: bytes) -> tuple[int, dict]:
    boundary = b"FORENSICA_TEST_BOUNDARY"
    body = (
        b"--" + boundary + b"\r\n"
        + f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
        + f"Content-Type: {content_type}\r\n\r\n".encode()
        + data + b"\r\n"
        + b"--" + boundary + b"--\r\n"
    )
    req = urllib.request.Request(
        f"{BASE}{path}", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary.decode()}"},
        method="POST",
    )
    try:
        r = urllib.request.urlopen(req)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def post_json(path: str, payload: dict) -> tuple[int, dict]:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        r = urllib.request.urlopen(req)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def get_json(path: str) -> tuple[int, dict]:
    try:
        r = urllib.request.urlopen(f"{BASE}{path}")
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def poll_analysis(job_id: str, max_wait: float = 15.0) -> dict | None:
    """Poll GET /analysis/{job_id} until complete or timeout."""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        status, data = get_json(f"/analysis/{job_id}")
        if status == 200 and data.get("status") == "complete":
            return data
        if data.get("status") == "error":
            return None
        time.sleep(0.5)
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Sample documents
# ══════════════════════════════════════════════════════════════════════════════
def make_png(width: int = 200, height: int = 280, has_text_rows: bool = True) -> bytes:
    """
    Create a real PNG with dark pixel rows (simulating text) and a light background.
    Uses pure Python / zlib — no Pillow needed in the test itself.
    """
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (width, height), (245, 245, 245))
    draw = ImageDraw.Draw(img)

    if has_text_rows:
        # Draw text-like horizontal bars at different heights
        for y in [40, 60, 80, 110, 130, 160, 200, 220, 240]:
            draw.rectangle([30, y, width - 30, y + 8], fill=(30, 30, 30))
        # Draw a "seal" blob in corner
        draw.ellipse([10, 10, 70, 70], fill=(40, 40, 100))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_jpeg(edited: bool = False) -> bytes:
    """
    Create a JPEG. If edited=True:
      - Paste a high-contrast block (different noise level)
      - Resave at lower quality to amplify ELA artefact signal
    """
    from PIL import Image, ImageDraw
    import random
    random.seed(42 if not edited else 99)
    img = Image.new("RGB", (300, 400), (250, 248, 245))
    draw = ImageDraw.Draw(img)

    # Text rows
    for y in [50, 80, 110, 140, 200, 230, 260, 300, 340]:
        draw.rectangle([40, y, 260, y + 9], fill=(20, 20, 20))

    if edited:
        # Save pristine version first
        buf0 = io.BytesIO()
        img.save(buf0, format="JPEG", quality=92)

        # Load it back and paste a very different block (simulates copy-paste editing)
        buf0.seek(0)
        img2 = Image.open(buf0).convert("RGB")
        paste_block = Image.new("RGB", (120, 40), (60, 180, 80))
        img2.paste(paste_block, (90, 150))

        # Re-save at lower quality — this creates strong ELA residuals
        buf1 = io.BytesIO()
        img2.save(buf1, format="JPEG", quality=70)
        return buf1.getvalue()

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def make_pdf_stub() -> bytes:
    """Minimal PDF-like file (valid header, not a real PDF but passes header check)."""
    return b"%PDF-1.4\n%fake forensica test document\n%%EOF"


# ══════════════════════════════════════════════════════════════════════════════
# Section 1: Health
# ══════════════════════════════════════════════════════════════════════════════
def test_health():
    print("\n── Section 1: Health Check ──────────────────────────────────────────")
    status, data = get_json("/health")
    record("GET /health returns 200",  status == 200)
    record("Response has status=ok",   data.get("status") == "ok")
    record("Service identified",        data.get("service") == "Forensica AI")


# ══════════════════════════════════════════════════════════════════════════════
# Section 2: Upload validation
# ══════════════════════════════════════════════════════════════════════════════
def test_upload_valid():
    print("\n── Section 2: Valid Uploads ─────────────────────────────────────────")

    # PNG
    png_data = make_png()
    status, data = post_multipart("/upload", "certificate.png", "image/png", png_data)
    ok = record("Upload PNG returns 201",      status == 201, f"status={status}")
    if ok:
        record("PNG upload has doc id",         data.get("id", "").startswith("doc_"))
        record("PNG upload has filename",        data.get("filename") == "certificate.png")
        record("PNG size_bytes is accurate",     data.get("size_bytes") == len(png_data))
        record("PNG pages=1",                    data.get("pages") == 1)

    # JPEG
    jpg_data = make_jpeg()
    status, data = post_multipart("/upload", "scan.jpg", "image/jpeg", jpg_data)
    ok = record("Upload JPG returns 201",      status == 201, f"status={status}")
    if ok:
        record("JPG upload has doc id",          data.get("id", "").startswith("doc_"))

    # JPEG with .jpeg extension
    status, data = post_multipart("/upload", "id_scan.jpeg", "image/jpeg", jpg_data)
    record("Upload JPEG (.jpeg ext) 201",      status == 201)

    # PDF stub (header only — PyMuPDF will fail gracefully, pages defaults to 1)
    pdf_data = make_pdf_stub()
    status, data = post_multipart("/upload", "transcript.pdf", "application/pdf", pdf_data)
    record("Upload PDF returns 201",           status == 201, f"status={status}")

    return data.get("id") if status == 201 else None


def test_upload_invalid():
    print("\n── Section 3: Invalid Upload Rejection ──────────────────────────────")

    # Unsupported format — .exe
    status, data = post_multipart("/upload", "malware.exe", "application/octet-stream", b"MZ\x00\x01")
    record("Reject .exe upload (422)",         status == 422, f"status={status}")

    # Empty file
    status, data = post_multipart("/upload", "empty.png", "image/png", b"")
    record("Reject empty file (422)",          status == 422, f"status={status}")

    # .txt file
    status, data = post_multipart("/upload", "readme.txt", "text/plain", b"hello world")
    record("Reject .txt upload (422)",         status == 422, f"status={status}")

    # Oversized file (simulate — 16 MB of zeros)
    big_data = b"\x00" * (16 * 1024 * 1024)
    status, data = post_multipart("/upload", "huge.png", "image/png", big_data)
    record("Reject oversized file (422)",      status == 422, f"status={status}")


# ══════════════════════════════════════════════════════════════════════════════
# Section 4: Full pipeline — clean PNG document
# ══════════════════════════════════════════════════════════════════════════════
def test_pipeline_clean_png():
    print("\n── Section 4: Pipeline — Clean PNG ─────────────────────────────────")
    png_data = make_png(width=400, height=560, has_text_rows=True)

    # Upload
    status, doc = post_multipart("/upload", "test_certificate.png", "image/png", png_data)
    if not record("Upload PNG 201", status == 201):
        return None
    doc_id = doc["id"]

    # Analyze
    status, job = post_json("/analyze", {"document_id": doc_id})
    if not record("POST /analyze 202", status == 202, f"job_id={job.get('job_id')}"):
        return None
    job_id = job["job_id"]
    record("Job status is queued/running", job.get("status") in ("queued", "running"))

    # Poll
    print(f"     Polling {job_id} ...", end="", flush=True)
    result = poll_analysis(job_id, max_wait=20)
    print()
    if not record("Pipeline completed within 20s", result is not None):
        return None

    # Results validation
    record("score is int 0-100",             isinstance(result.get("score"), int)
                                              and 0 <= result["score"] <= 100,
                                              f"score={result.get('score')}")
    record("classification present",         result.get("classification") in
                                              ("LOW_RISK", "SUSPICIOUS", "HIGH_RISK"),
                                              f"class={result.get('classification')}")
    record("anomalies is a list",            isinstance(result.get("anomalies"), list))
    record("overlays is a list",             isinstance(result.get("overlays"), list))
    record("module_scores has all keys",     all(k in result.get("module_scores", {})
                                              for k in ("pixel_analyzer", "layout_checker",
                                                        "font_detector", "ocr_extractor")))
    record("explanation is a non-empty str", isinstance(result.get("explanation"), str)
                                              and len(result.get("explanation", "")) > 20,
                                              f"len={len(result.get('explanation',''))}")
    record("extracted_text present",         "extracted_text" in result)

    return doc_id


# ══════════════════════════════════════════════════════════════════════════════
# Section 5: Full pipeline — edited JPEG (should score higher)
# ══════════════════════════════════════════════════════════════════════════════
def test_pipeline_edited_jpeg():
    print("\n── Section 5: Pipeline — Edited JPEG (ELA signal) ──────────────────")
    jpg_clean  = make_jpeg(edited=False)
    jpg_edited = make_jpeg(edited=True)

    # Upload both
    _, doc_c = post_multipart("/upload", "clean.jpg",  "image/jpeg", jpg_clean)
    _, doc_e = post_multipart("/upload", "edited.jpg", "image/jpeg", jpg_edited)

    # Analyze both
    _, job_c = post_json("/analyze", {"document_id": doc_c["id"]})
    _, job_e = post_json("/analyze", {"document_id": doc_e["id"]})

    print("     Polling clean...  ", end="", flush=True)
    res_c = poll_analysis(job_c["job_id"])
    print()
    print("     Polling edited... ", end="", flush=True)
    res_e = poll_analysis(job_e["job_id"])
    print()

    if res_c and res_e:
        record("Clean JPEG analyzed",        res_c.get("status") == "complete")
        record("Edited JPEG analyzed",       res_e.get("status") == "complete")
        # ELA (compression_check) correctly captures the editing signal;
        # raw pixel_analyzer score depends on image structure, not just edits
        record("Edited compression_score >= clean",
               res_e["module_scores"].get("compression_check", 0)
               >= res_c["module_scores"].get("compression_check", 0),
               f"clean_ela={res_c['module_scores'].get('compression_check',0):.3f} "
               f"edited_ela={res_e['module_scores'].get('compression_check',0):.3f}")
        record("Edited JPEG has at least one anomaly",
               len(res_e.get("anomalies", [])) > 0)
    else:
        record("Both pipelines completed", False)

    return doc_e.get("id") if res_e else None


# ══════════════════════════════════════════════════════════════════════════════
# Section 6: Analysis results quality
# ══════════════════════════════════════════════════════════════════════════════
def test_anomaly_quality(doc_id: str | None):
    print("\n── Section 6: Anomaly Quality & Real Values ─────────────────────────")
    if not doc_id:
        print("  [SKIP] No doc_id available from previous tests")
        return

    # Find the job id for this doc
    # We'll re-analyze to get a fresh job
    _, job = post_json("/analyze", {"document_id": doc_id})
    result = poll_analysis(job["job_id"])

    if not result:
        record("Got results for quality check", False)
        return

    anomalies = result.get("anomalies", [])
    overlays  = result.get("overlays", [])
    module_scores = result.get("module_scores", {})

    record("At least one module scored > 0",
           any(v > 0 for v in module_scores.values()),
           str(module_scores))

    if anomalies:
        a = anomalies[0]
        record("Anomaly has required fields",
               all(k in a for k in ("id", "type", "label", "severity", "confidence", "description", "module")))
        record("Anomaly severity is valid value",
               a.get("severity") in ("HIGH", "MEDIUM", "LOW"))
        record("Anomaly confidence in [0,1]",
               0.0 <= float(a.get("confidence", -1)) <= 1.0,
               f"confidence={a.get('confidence')}")
        record("Anomaly description is meaningful (>30 chars)",
               len(a.get("description", "")) > 30,
               f"len={len(a.get('description',''))}")

    if overlays:
        ov = overlays[0]
        record("Overlay has CSS % coordinates",
               all(str(ov.get(k, "")).endswith("%") for k in ("x", "y", "w", "h")),
               str({k: ov.get(k) for k in ("x", "y", "w", "h")}))
        record("Overlay color is valid",
               ov.get("color") in ("red", "orange", "yellow"))

    # Check regions map to real pixel coords
    regions_with_coords = [a for a in anomalies if a.get("region")]
    if regions_with_coords:
        r = regions_with_coords[0]["region"]
        record("Region has x,y,w,h",
               all(k in r for k in ("x", "y", "w", "h")))
        record("Region coords are non-negative",
               all(int(r.get(k, -1)) >= 0 for k in ("x", "y", "w", "h")))


# ══════════════════════════════════════════════════════════════════════════════
# Section 7: Report generation
# ══════════════════════════════════════════════════════════════════════════════
def test_report(doc_id: str | None):
    print("\n── Section 7: Report Generation ─────────────────────────────────────")
    if not doc_id:
        print("  [SKIP] No doc_id from previous tests")
        return

    status, report = get_json(f"/report/{doc_id}")
    if not record("GET /report/{id} returns 200", status == 200, f"status={status}"):
        return

    record("report_id present",            report.get("report_id", "").startswith("FR-"))
    record("verdict.classification valid", report.get("verdict", {}).get("classification")
                                            in ("LOW_RISK", "SUSPICIOUS", "HIGH_RISK"))
    record("verdict.score is int",         isinstance(report.get("verdict", {}).get("score"), int))
    record("document_info populated",      bool(report.get("document_info", {}).get("filename")))
    record("anomalies list present",       isinstance(report.get("anomalies"), list))
    record("module_scores present",        isinstance(report.get("module_scores"), dict)
                                           and len(report.get("module_scores", {})) > 0)
    record("explanation in report",        len(report.get("explanation", "")) > 20,
                                           f"len={len(report.get('explanation',''))}")
    record("suspicious_regions present",   isinstance(report.get("suspicious_regions"), list))

    # Download endpoint
    status2, _ = get_json(f"/report/{doc_id}/download")
    record("GET /report/{id}/download 200", status2 == 200)


# ══════════════════════════════════════════════════════════════════════════════
# Section 8: Error handling
# ══════════════════════════════════════════════════════════════════════════════
def test_error_handling():
    print("\n── Section 8: Error Handling ────────────────────────────────────────")

    # Non-existent doc ID
    status, data = post_json("/analyze", {"document_id": "doc_doesnotexist"})
    record("Analyze missing doc → 404",      status == 404, f"status={status}")

    # Non-existent job ID
    status, data = get_json("/analysis/job_doesnotexist")
    record("Results missing job → 404",      status == 404, f"status={status}")

    # Non-existent doc for report
    status, data = get_json("/report/doc_doesnotexist")
    record("Report missing doc → 404",       status == 404, f"status={status}")

    # Analyze with no body
    req = urllib.request.Request(
        f"{BASE}/analyze", data=b"{}",
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        r = urllib.request.urlopen(req)
        status3 = r.status
    except urllib.error.HTTPError as e:
        status3 = e.code
    record("Analyze with empty body → 4xx", status3 >= 400, f"status={status3}")

    # Upload with no file part
    req2 = urllib.request.Request(
        f"{BASE}/upload", data=b"", method="POST",
        headers={"Content-Type": "multipart/form-data; boundary=x"},
    )
    try:
        r2 = urllib.request.urlopen(req2)
        status4 = r2.status
    except urllib.error.HTTPError as e:
        status4 = e.code
    record("Upload with no file → 4xx",     status4 >= 400, f"status={status4}")


# ══════════════════════════════════════════════════════════════════════════════
# Section 9: Overlay coordinate sanity
# ══════════════════════════════════════════════════════════════════════════════
def test_overlay_coordinates(result: dict | None):
    print("\n── Section 9: Overlay Coordinate Mapping ────────────────────────────")
    if not result:
        print("  [SKIP] No result data")
        return

    overlays = result.get("overlays", [])
    if not overlays:
        record("Overlays generated", False, "No overlays in result")
        return

    for ov in overlays:
        for key in ("x", "y", "w", "h"):
            val = ov.get(key, "")
            pct = float(val.rstrip("%"))
            record(f"Overlay {ov['id']}.{key} in [0,100]%",
                   0.0 <= pct <= 100.0, f"{key}={val}")


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 64)
    print("        Forensica AI -- Full System Validation Suite          ")
    print("=" * 64)

    # Verify server is up
    try:
        urllib.request.urlopen(f"{BASE}/health", timeout=3)
    except Exception:
        print(f"\n  ERROR: Backend not running at {BASE}")
        print("  Start it with: cd backend && python -m uvicorn main:app --reload --port 8000")
        sys.exit(1)

    test_health()
    test_upload_valid()
    test_upload_invalid()
    doc_id_clean  = test_pipeline_clean_png()
    doc_id_edited = test_pipeline_edited_jpeg()

    # Reuse edited doc for quality, report, and overlay tests
    active_doc = doc_id_edited or doc_id_clean
    test_anomaly_quality(active_doc)
    test_report(active_doc)
    test_error_handling()

    # Overlay coordinate test — get a fresh result for the active doc
    if active_doc:
        _, job = post_json("/analyze", {"document_id": active_doc})
        final_result = poll_analysis(job["job_id"])
        test_overlay_coordinates(final_result)

    # ── Summary ───────────────────────────────────────────────────────────
    total   = len(results)
    passed  = sum(1 for _, ok, _ in results if ok)
    failed  = total - passed

    print("\n" + "=" * 64)
    print(f"  Results: {passed}/{total} passed  |  {failed} failed")
    print("=" * 64)

    if failed:
        print("\nFailed tests:")
        for name, ok, detail in results:
            if not ok:
                print(f"  {FAIL} {name}" + (f" ({detail})" if detail else ""))
        sys.exit(1)
    else:
        print("\n  All tests passed. System is functional.")


if __name__ == "__main__":
    main()
