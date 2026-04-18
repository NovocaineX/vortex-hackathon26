"""
smoke_test.py - End-to-end API smoke test for Forensica AI backend.
Run from: c:/Users/aadar/Desktop/hackathon/
    python smoke_test.py
"""
import urllib.request
import json
import time
import io
import struct
import zlib

BASE = "http://localhost:8000"


def make_tiny_png():
    """Create a minimal valid 1x1 red PNG."""
    def chunk(name, data):
        c = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", c)

    sig  = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    idat = chunk(b"IDAT", zlib.compress(b"\x00\xFF\x00\xFF"))
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


def post_multipart(url, field_name, filename, content_type, data):
    boundary = b"FORENSICABOUNDARY"
    body = (
        b"--" + boundary + b"\r\n"
        + f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode()
        + f"Content-Type: {content_type}\r\n\r\n".encode()
        + data + b"\r\n"
        + b"--" + boundary + b"--\r\n"
    )
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary.decode()}"},
        method="POST",
    )
    return urllib.request.urlopen(req)


def post_json(url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return urllib.request.urlopen(req)


def get_json(url):
    return urllib.request.urlopen(url)


# ── Health check ────────────────────────────────────────────────────────────
print("\n=== Forensica AI Smoke Test ===\n")
r = get_json(f"{BASE}/health")
health = json.loads(r.read())
print(f"[HEALTH] status={health['status']}  version={health['version']}")

# ── Upload ──────────────────────────────────────────────────────────────────
png = make_tiny_png()
r2  = post_multipart(f"{BASE}/upload", "file", "test_cert.png", "image/png", png)
doc = json.loads(r2.read())
doc_id = doc["id"]
print(f"[UPLOAD] id={doc_id}  filename={doc['filename']}  size={doc['size_bytes']}B  pages={doc['pages']}")

# ── Analyze ─────────────────────────────────────────────────────────────────
r3  = post_json(f"{BASE}/analyze", {"document_id": doc_id})
job = json.loads(r3.read())
job_id = job["job_id"]
print(f"[ANALYZE] job_id={job_id}  status={job['status']}")

# ── Poll results ─────────────────────────────────────────────────────────────
print("[POLL] Waiting for pipeline to complete...")
for attempt in range(10):
    time.sleep(0.8)
    try:
        r4     = get_json(f"{BASE}/analysis/{job_id}")
        result = json.loads(r4.read())
        if result.get("status") == "complete":
            break
    except urllib.error.HTTPError as e:
        if e.code == 202:
            continue
        raise

print(f"[RESULTS] score={result.get('score')}  class={result.get('classification')}  anomalies={len(result.get('anomalies', []))}")
print(f"          overlays={len(result.get('overlays', []))}  modules={list(result.get('module_scores', {}).keys())}")

# ── Report ───────────────────────────────────────────────────────────────────
r5     = get_json(f"{BASE}/report/{doc_id}")
report = json.loads(r5.read())
print(f"[REPORT] id={report.get('report_id')}  verdict={report.get('verdict', {}).get('classification')}")
print(f"         anomaly_rows={len(report.get('anomalies', []))}  module_scores={len(report.get('module_scores', {}))}")

print("\n=== All tests passed! ===\n")
