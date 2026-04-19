/**
 * api.js — Forensica AI API Client Layer
 *
 * Central module for all backend communication.
 * All fetch calls are routed through here so swapping
 * from mock → real backend only requires changing BASE_URL.
 */

// ── Configuration ─────────────────────────────────────────────
// To use the real FastAPI backend:
//   1. cd backend && uvicorn main:app --reload --port 8000
//   2. Change MOCK_MODE to false below
import { getAuthToken } from './auth.js';

const LIVE_BACKEND_URL = 'https://forensica-backend.onrender.com';
const LOCAL_BACKEND_URL = 'http://localhost:8000';

const API_CONFIG = {
  // If viewing on Netlify/Internet, hit the Cloud. If local, hit the local python server.
  BASE_URL: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
            ? LOCAL_BACKEND_URL 
            : LIVE_BACKEND_URL,
  TIMEOUT_MS: 30_000,
  MOCK_MODE: false,
};

/**
 * Check whether the FastAPI backend is reachable.
 * Call this on app startup to auto-switch to live mode.
 *
 * Usage in app.js:
 *   const live = await checkBackendHealth();
 *   if (live) API_CONFIG.MOCK_MODE = false;
 */
export async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_CONFIG.BASE_URL}/health`, {
      signal: AbortSignal.timeout(2000),
    });
    if (res.ok) {
      API_CONFIG.MOCK_MODE = false;
      console.info('[Forensica] Backend detected — using live API mode.');
      return true;
    }
  } catch (_) { /* backend not running */ }
  console.info('[Forensica] Backend not found — using mock mode.');
  return false;
}

// ── Request helper ─────────────────────────────────────────────
async function request(method, path, body = null, isFormData = false) {
  if (API_CONFIG.MOCK_MODE) {
    return _mockDispatch(method, path, body);
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), API_CONFIG.TIMEOUT_MS);

  const headers = isFormData ? {} : { 'Content-Type': 'application/json' };
  const token = await getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const opts = {
    method,
    signal: controller.signal,
    headers,
  };
  if (body) opts.body = isFormData ? body : JSON.stringify(body);

  try {
    const res = await fetch(`${API_CONFIG.BASE_URL}${path}`, opts);
    clearTimeout(timeout);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiError(err.detail || `HTTP ${res.status}`, res.status);
    }
    return await res.json();
  } catch (e) {
    clearTimeout(timeout);
    if (e.name === 'AbortError') throw new ApiError('Request timed out', 408);
    throw e;
  }
}

// ── Custom error ───────────────────────────────────────────────
export class ApiError extends Error {
  constructor(message, status = 500) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

// ── Public API methods ─────────────────────────────────────────

/**
 * POST /upload
 * Upload a document file for analysis.
 * @param {File} file
 * @returns {{ id: string, pages: number, filename: string }}
 */
export async function uploadDocument(file) {
  const form = new FormData();
  form.append('file', file);
  return request('POST', '/upload', form, true);
}

/**
 * POST /analyze
 * Start the detection pipeline for an uploaded document.
 * @param {string} documentId
 * @returns {{ job_id: string, status: string }}
 */
export async function startAnalysis(documentId) {
  return request('POST', '/analyze', { document_id: documentId });
}

/**
 * GET /analysis/{id}
 * Poll for analysis results.
 * @param {string} jobId
 * @returns {{ status, score, classification, anomalies[], overlays[] }}
 */
export async function getAnalysisResults(jobId) {
  return request('GET', `/analysis/${jobId}`);
}

/**
 * GET /report/{id}
 * Fetch the structured verification report.
 * @param {string} documentId
 * @returns {{ report_id, verdict, anomalies[], module_scores, download_url }}
 */
export async function getReport(documentId) {
  return request('GET', `/report/${documentId}`);
}

/**
 * GET /preview/{documentId}
 * Returns the URL to load the document preview image.
 * In live mode this is a direct backend URL; in mock mode returns null.
 * @param {string} documentId
 * @returns {string|null}
 */
export function getPreviewUrl(documentId) {
  if (API_CONFIG.MOCK_MODE) return null;
  return `${API_CONFIG.BASE_URL}/preview/${documentId}`;
}

// ── Mock implementations ───────────────────────────────────────
// These mirror the exact JSON contract the real FastAPI backend will return.
function _mockDispatch(method, path, body) {
  if (method === 'POST' && path === '/upload')          return _mockUpload(body);
  if (method === 'POST' && path === '/analyze')         return _mockStartAnalysis(body);
  if (method === 'GET' && path.startsWith('/analysis')) return _mockResults(path);
  if (method === 'GET' && path.startsWith('/report'))   return _mockReport(path);
  return Promise.reject(new ApiError(`No mock for ${method} ${path}`, 404));
}

function _mockUpload(form) {
  return new Promise((resolve) => {
    setTimeout(() => resolve({
      id: 'doc_' + Math.random().toString(36).slice(2, 10),
      filename: form?.get ? form.get('file')?.name ?? 'document.pdf' : 'document.pdf',
      pages: 1,
      size_bytes: form?.get ? form.get('file')?.size ?? 0 : 0,
      uploaded_at: new Date().toISOString(),
    }), 900);
  });
}

function _mockStartAnalysis({ document_id }) {
  return new Promise((resolve) => {
    setTimeout(() => resolve({
      job_id: 'job_' + Math.random().toString(36).slice(2, 10),
      document_id,
      status: 'queued',
      created_at: new Date().toISOString(),
    }), 300);
  });
}

function _mockResults(path) {
  // Simulate a short delay then return complete results
  return new Promise((resolve) => {
    setTimeout(() => resolve({
      job_id: path.split('/').pop(),
      status: 'complete',
      score: 70,
      classification: 'HIGH_RISK',
      anomalies: [
        {
          id: 'a1', type: 'font_inconsistency', severity: 'HIGH', confidence: 0.82,
          label: 'Font Inconsistency',
          description: 'Two distinct font families detected in the certificate name field. Glyph metrics suggest copy-paste editing from a different source document.',
          region: { x: 550, y: 120, w: 350, h: 80 },
          module: 'font_detector',
        },
        {
          id: 'a2', type: 'pixel_cloning', severity: 'HIGH', confidence: 0.74,
          label: 'Pixel Cloning',
          description: 'Clone stamp artifacts detected in the institutional seal area. Noise pattern is inconsistent with surrounding content.',
          region: { x: 50, y: 100, w: 180, h: 180 },
          module: 'pixel_analyzer',
        },
        {
          id: 'a3', type: 'layout_irregularity', severity: 'MEDIUM', confidence: 0.61,
          label: 'Layout Irregularity',
          description: 'Footer signature block is 3.2 mm below expected grid position. Margin ratios deviate from template baseline.',
          region: { x: 80, y: 750, w: 400, h: 90 },
          module: 'layout_checker',
        },
        {
          id: 'a4', type: 'compression_artifact', severity: 'LOW', confidence: 0.38,
          label: 'Compression Artifact',
          description: 'JPEG re-compression artifacts detected. Quality inconsistencies suggest multi-generation editing.',
          region: null,
          module: 'pixel_analyzer',
        },
      ],
      module_scores: {
        font_detector:   0.82,
        layout_checker:  0.75,
        pixel_analyzer:  0.68,
        ocr_extractor:   0.42,
        compression_check: 0.38,
      },
      overlays: [
        { id: 'a1', color: 'red',    x: '55%', y: '12%', w: '35%', h: '12%', label: 'Font Anomaly' },
        { id: 'a2', color: 'orange', x: '5%',  y: '10%', w: '18%', h: '18%', label: 'Pixel Clone' },
        { id: 'a3', color: 'yellow', x: '10%', y: '75%', w: '38%', h: '10%', label: 'Layout Error' },
      ],
      completed_at: new Date().toISOString(),
    }), 1400);
  });
}

function _mockReport(path) {
  return new Promise((resolve) => {
    setTimeout(() => resolve({
      report_id: 'FR-2024-00847',
      document_id: path.split('/').pop(),
      generated_at: new Date().toISOString(),
      verdict: { classification: 'HIGH_RISK', score: 70, recommendation: 'Do not accept without manual expert review.' },
      document_info: {
        filename: 'Certificate_2024.pdf',
        type: 'Academic Certificate',
        size_bytes: 2516582,
        pages: 1,
      },
      anomalies: [
        { id: 'a1', type: 'Font Inconsistency',  severity: 'HIGH',   confidence: 0.82, region: '(550,120)→(900,200)' },
        { id: 'a2', type: 'Pixel Cloning',        severity: 'HIGH',   confidence: 0.74, region: '(50,100)→(230,280)' },
        { id: 'a3', type: 'Layout Irregularity',  severity: 'MEDIUM', confidence: 0.61, region: '(80,750)→(480,840)' },
        { id: 'a4', type: 'Compression Artifact', severity: 'LOW',    confidence: 0.38, region: 'Global' },
      ],
      module_scores: {
        'Font Inconsistency Detection':  0.82,
        'Layout Consistency Check':      0.75,
        'Pixel Anomaly Detection':       0.68,
        'OCR Text Extraction':           0.42,
        'Compression Analysis':          0.38,
      },
      download_url: '/report/FR-2024-00847/download',
    }), 500);
  });
}
