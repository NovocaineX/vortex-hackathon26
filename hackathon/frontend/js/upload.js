/**
 * upload.js — Document Upload Module
 *
 * Handles drag-and-drop, file validation, upload progress,
 * and analysis pipeline triggering. Communicates exclusively
 * through the api.js client layer.
 */

import { uploadDocument, startAnalysis, getAnalysisResults, getPreviewUrl } from './api.js';
import { appState, setState } from './state.js';
import { $, fmtBytes, toast, animateCounter, SEV_CLASS, incrementNotifBadge } from './utils.js';
import { navigateTo } from './router.js';
import { renderResults } from './results.js';
import { addToHistory } from './history.js';

// ── Constants ──────────────────────────────────────────────────
const ALLOWED_TYPES = new Set(['application/pdf', 'image/jpeg', 'image/png']);
const ALLOWED_EXTS  = new Set(['.pdf', '.jpg', '.jpeg', '.png']);
const MAX_BYTES     = 15 * 1024 * 1024; // 15 MB

const ANALYSIS_STEPS = [
  { id: 'step0', label: 'Queueing',                    ms: 500 },
  { id: 'step1', label: 'OCR Text Extraction',          ms: 1200 },
  { id: 'step2', label: 'Pixel Anomaly Detection',      ms: 1600 },
  { id: 'step3', label: 'Layout Consistency Check',     ms: 1100 },
  { id: 'step4', label: 'Font Inconsistency Detection', ms: 1300 },
  { id: 'step5', label: 'Explainability Engine',        ms: 900 },
];

// ── Init ───────────────────────────────────────────────────────
export function initUpload() {
  const dropzone   = $('dropzone');
  const fileInput  = $('fileInput');
  const browseBtn  = $('browseBtn');

  if (!dropzone) return;

  browseBtn.addEventListener('click', (e) => { e.stopPropagation(); fileInput.click(); });
  dropzone.addEventListener('click', () => fileInput.click());

  dropzone.addEventListener('dragover',  (e) => { e.preventDefault(); dropzone.classList.add('drag-over'); });
  dropzone.addEventListener('dragleave', ()  => dropzone.classList.remove('drag-over'));
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) handleFile(fileInput.files[0]);
  });

  $('clearUploadBtn')?.addEventListener('click', clearUpload);
  $('startAnalysisBtn')?.addEventListener('click', runAnalysisPipeline);
  $('viewResultsBtn')?.addEventListener('click', () => navigateTo('results'));
  $('newAnalysisBtn')?.addEventListener('click', () => { clearUpload(); navigateTo('upload'); });
}

// ── File handling ──────────────────────────────────────────────
function handleFile(file) {
  const ext = '.' + file.name.split('.').pop().toLowerCase();
  if (!ALLOWED_TYPES.has(file.type) && !ALLOWED_EXTS.has(ext)) {
    toast('Unsupported file type. Please upload PDF, JPG, or PNG.', 'error');
    return;
  }
  if (file.size > MAX_BYTES) {
    toast('File too large. Maximum size is 15 MB.', 'error');
    return;
  }

  setState({ uploadStatus: 'uploading', currentFile: file });

  // Update UI to file-selected state
  $('dropzoneInner').classList.add('hidden');
  $('fileInfo').classList.remove('hidden');
  $('fileName').textContent = file.name;
  $('fileSize').textContent = fmtBytes(file.size);

  // Animate progress then call upload API
  animateProgressBar().then(async () => {
    try {
      setState({ uploadStatus: 'uploading' });

      // POST /upload
      const doc = await uploadDocument(file);
      setState({ document: doc, uploadStatus: 'uploaded' });

      // Update downstream displays
      if ($('resultsFileName')) $('resultsFileName').textContent = doc.filename;
      if ($('rptFileName'))     $('rptFileName').textContent     = doc.filename;

      showDocumentPreview();
      $('startAnalysisBtn').disabled = false;
      toast('Document uploaded successfully!', 'success');
    } catch (err) {
      setState({ uploadStatus: 'error' });
      toast(`Upload failed: ${err.message}`, 'error');
      clearUpload();
    }
  });
}

function animateProgressBar() {
  return new Promise((resolve) => {
    const fill  = $('progressFill');
    const pct   = $('progressPct');
    const label = $('progressLabel');
    let progress = 0;

    const tick = setInterval(() => {
      progress += Math.random() * 16 + 6;
      if (progress >= 100) {
        progress = 100;
        clearInterval(tick);
        if (label) label.textContent = 'Upload Complete';
        if (fill)  fill.style.width = '100%';
        if (pct)   pct.textContent  = '100%';
        setTimeout(resolve, 350);
      } else {
        if (fill) fill.style.width = progress + '%';
        if (pct)  pct.textContent  = Math.round(progress) + '%';
      }
    }, 110);
  });
}

function showDocumentPreview() {
  $('previewEmpty')?.classList.add('hidden');
  $('previewDoc')?.classList.remove('hidden');

  // Swap simulated wireframe for real document image (live backend only)
  const docId = appState.document?.id ?? appState.document?.document_id;
  const previewUrl = docId ? getPreviewUrl(docId) : null;
  const simDoc = $('simDoc');

  if (previewUrl && simDoc) {
    let previewImg = $('docPreviewImg');
    if (!previewImg) {
      previewImg = document.createElement('img');
      previewImg.id = 'docPreviewImg';
      previewImg.alt = 'Document Preview';
      previewImg.style.cssText = 'width:100%;height:100%;object-fit:contain;border-radius:4px;display:block;';
      simDoc.insertBefore(previewImg, simDoc.firstChild);
    }

    // Graceful fallback — if preview fails, just keep wireframe visible
    previewImg.onerror = () => {
      previewImg.style.display = 'none';
      simDoc.querySelectorAll('.sim-header,.sim-body,.sim-footer').forEach(el => {
        el.style.display = '';
      });
    };

    previewImg.src = previewUrl;
    previewImg.style.display = 'block';
    simDoc.style.cssText = 'position:relative;background:transparent;padding:0;border-radius:4px;overflow:hidden;';
    simDoc.querySelectorAll('.sim-header,.sim-body,.sim-footer').forEach(el => {
      el.style.display = 'none';
    });
  }
}


function clearUpload() {
  setState({ document: null, uploadStatus: 'idle', job: null, results: null, analysisStatus: 'idle' });
  $('fileInput').value = '';
  $('dropzoneInner')?.classList.remove('hidden');
  $('fileInfo')?.classList.add('hidden');
  $('previewEmpty')?.classList.remove('hidden');
  $('previewDoc')?.classList.add('hidden');
  $('startAnalysisBtn').disabled = true;
  $('progressFill').style.width = '0%';
  $('progressPct').textContent  = '0%';
  $('progressLabel').textContent = 'Uploading...';
  $('viewResultsBtn')?.classList.add('hidden');
  $('statScore').textContent = '—';
  $('statAnomalies').textContent = '—';
  $('statRisk').textContent = '—';
  $('jobStatusBadge').textContent = 'Idle';
  $('jobStatusBadge').dataset.status = 'idle';
  resetStepLog();
  // Hide preview overlays
  ['overlay1','overlay2','overlay3'].forEach(id => $(id)?.classList.add('hidden'));
  // Reset real preview image if shown
  const previewImg = $('docPreviewImg');
  if (previewImg) previewImg.style.display = 'none';
  const simDoc = $('simDoc');
  if (simDoc) simDoc.querySelectorAll('.sim-header,.sim-body,.sim-footer').forEach(el => { el.style.display = ''; });
  toast('Upload cleared.', 'info');
}

// ── Analysis pipeline ──────────────────────────────────────────
async function runAnalysisPipeline() {
  if (!appState.document) { toast('Please upload a document first.', 'warn'); return; }

  const btn = $('startAnalysisBtn');
  btn.disabled = true;
  btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-.03-4.7"/></svg> Analyzing…`;

  $('jobStatusBadge').textContent = 'Running';
  $('jobStatusBadge').dataset.status = 'running';
  setState({ analysisStatus: 'running' });

  let jobResp;
  try {
    // POST /analyze — this returns quickly with a job_id
    jobResp = await startAnalysis(appState.document.document_id ?? appState.document.id);
    setState({ job: jobResp });
  } catch (err) {
    setState({ analysisStatus: 'error' });
    $('jobStatusBadge').textContent = 'Error';
    $('jobStatusBadge').dataset.status = 'error';
    toast(`Analysis failed: ${err.message}`, 'error');
    btn.disabled = false;
    btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Start Analysis`;
    return;
  }

  // ── Non-blocking: re-enable UI immediately so the user can navigate away ──
  btn.disabled = false;
  btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Start Analysis`;
  toast('Analysis running in background — you can navigate freely.', 'info', 4000);

  // Capture snapshot of document for history (document may change if user re-uploads)
  const docSnapshot = { ...appState.document };
  const jobId = jobResp.analysis_id ?? jobResp.job_id;

  // ── Continue pipeline in background ───────────────────────────
  _runBackgroundPipeline(docSnapshot, jobId);
}

async function _runBackgroundPipeline(doc, jobId) {
  try {
    // Visual step log (best-effort; elements may be hidden if user navigated away)
    for (let i = 0; i < ANALYSIS_STEPS.length; i++) {
      await runStep(i, ANALYSIS_STEPS[i].ms);
    }

    // GET /analysis/{id}
    const results = await getAnalysisResults(jobId);
    setState({ results, analysisStatus: 'complete' });

    // Save to history store
    addToHistory(doc, results);

    // Update quick stats (if upload page still visible)
    const statScore = $('statScore');
    if (statScore) animateCounter(statScore, results.score, 800, '%');
    const statAno = $('statAnomalies');
    if (statAno) statAno.textContent = results.anomalies.length;
    const statRisk = $('statRisk');
    if (statRisk) statRisk.textContent = results.classification.replace('_', ' ');

    const badge = $('jobStatusBadge');
    if (badge) { badge.textContent = 'Complete'; badge.dataset.status = 'done'; }

    // Show overlays on upload preview (if still on that page)
    results.overlays?.forEach(ov => $(ov.id)?.classList.remove('hidden'));
    $('viewResultsBtn')?.classList.remove('hidden');

    // Pre-populate results page
    renderResults(results);

    // ── Non-blocking toast notification ───────────────────────────
    const riskLabel = results.classification.replace('_', ' ');
    toast(
      `✅ Analysis complete — ${doc.filename}<br><strong>${riskLabel}</strong> · ${results.anomalies.length} anomalies detected.`,
      results.classification === 'HIGH_RISK' ? 'error' : results.classification === 'SUSPICIOUS' ? 'warn' : 'success',
      6000
    );

    // Increment notification bell
    incrementNotifBadge();
  } catch (err) {
    setState({ analysisStatus: 'error' });
    const badge = $('jobStatusBadge');
    if (badge) { badge.textContent = 'Error'; badge.dataset.status = 'error'; }
    toast(`Analysis failed: ${err.message}`, 'error');
  }
}

function runStep(index, delayMs) {
  return new Promise((resolve) => {
    const el = $('step' + index);
    if (!el) { setTimeout(resolve, delayMs); return; }
    el.classList.remove('pending');
    el.classList.add('current');
    setTimeout(() => {
      el.classList.remove('current');
      el.classList.add('complete');
      const icon = el.querySelector('.step-icon');
      if (icon) icon.innerHTML = `<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3.5"><polyline points="20 6 9 17 4 12"/></svg>`;
      resolve();
    }, delayMs);
  });
}

function resetStepLog() {
  for (let i = 0; i <= 5; i++) {
    const el = $('step' + i);
    if (el) {
      el.className = 'step-item pending';
      const icon = el.querySelector('.step-icon');
      if (icon) icon.innerHTML = '';
    }
  }
}

// ── Zoom controls (upload preview) ────────────────────────────
export function initUploadViewer() {
  let zoom = 100;
  const update = () => { if ($('zoomLevel')) $('zoomLevel').textContent = zoom + '%'; };
  $('zoomInBtn')?.addEventListener('click',  () => { zoom = Math.min(zoom + 15, 200); update(); });
  $('zoomOutBtn')?.addEventListener('click', () => { zoom = Math.max(zoom - 15,  40); update(); });
  $('fitBtn')?.addEventListener('click',     () => { zoom = 100; update(); });

  // Overlay toggles
  $('toggleBBox')?.addEventListener('change', (e) => {
    ['overlay1','overlay2','overlay3'].forEach(id => {
      const el = $(id);
      if (el) el.style.display = e.target.checked ? 'block' : 'none';
    });
  });
}
