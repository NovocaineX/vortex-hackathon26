/**
 * batch.js — Multi-Document Batch Processing Module
 *
 * Allows users to upload multiple documents at once.
 * A concurrency-controlled queue processes up to 2 documents
 * in parallel, tracking each item's state independently in
 * a responsive grid layout.
 */

import { uploadDocument, startAnalysis, getAnalysisResults } from './api.js';
import { $, fmtBytes, toast } from './utils.js';
import { addToHistory } from './history.js';

// ── Constants ──────────────────────────────────────────────────
const ALLOWED_EXTS    = new Set(['.pdf', '.jpg', '.jpeg', '.png']);
const MAX_BYTES       = 15 * 1024 * 1024;
const MAX_CONCURRENCY = 2;

// ── State ──────────────────────────────────────────────────────
let batchQueue = [];      // Array of { id, file, status, result, error }
let activeCount = 0;      // Running analysis slots

// ── Init ───────────────────────────────────────────────────────
export function initBatch() {
  const dropzone    = $('batchDropzone');
  const fileInput   = $('batchFileInput');
  const browseBtn   = $('batchBrowseBtn');
  const runBtn      = $('batchRunBtn');
  const clearBtn    = $('batchClearBtn');

  if (!dropzone) return;

  browseBtn?.addEventListener('click', (e) => { e.stopPropagation(); fileInput?.click(); });
  dropzone.addEventListener('click', () => fileInput?.click());

  dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('drag-over'); });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('drag-over');
    addFiles([...e.dataTransfer.files]);
  });

  fileInput?.addEventListener('change', () => {
    if (fileInput.files.length) addFiles([...fileInput.files]);
    fileInput.value = '';
  });

  runBtn?.addEventListener('click', runBatch);
  clearBtn?.addEventListener('click', clearBatch);
}

export function onBatchPageEnter() {
  renderQueue();
  updateBatchControls();
}

// ── File ingestion ─────────────────────────────────────────────
function addFiles(files) {
  let added = 0;
  files.forEach(file => {
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED_EXTS.has(ext)) {
      toast(`Skipped ${file.name} — unsupported type`, 'warn');
      return;
    }
    if (file.size > MAX_BYTES) {
      toast(`Skipped ${file.name} — exceeds 15 MB`, 'warn');
      return;
    }
    // Deduplicate by name+size
    const dup = batchQueue.find(q => q.file.name === file.name && q.file.size === file.size);
    if (dup) { toast(`${file.name} already in queue`, 'info'); return; }
    batchQueue.push({ id: 'q_' + Math.random().toString(36).slice(2, 9), file, status: 'pending', result: null, error: null });
    added++;
  });
  if (added) { renderQueue(); updateBatchControls(); }
  if (added === 1) toast(`Added ${files[0].name}`, 'success');
  else if (added > 1) toast(`Added ${added} files to batch queue`, 'success');
}

// ── Queue controls ─────────────────────────────────────────────
function runBatch() {
  const pending = batchQueue.filter(q => q.status === 'pending' || q.status === 'error');
  if (!pending.length) { toast('No pending items to process', 'info'); return; }
  pending.forEach(item => { item.status = 'queued'; });
  renderQueue();
  updateBatchControls();
  drainQueue();
}

function clearBatch() {
  const hasActive = batchQueue.some(q => q.status === 'running');
  if (hasActive) { toast('Cannot clear while items are running', 'warn'); return; }
  batchQueue = [];
  activeCount = 0;
  renderQueue();
  updateBatchControls();
}

// ── Concurrency engine ─────────────────────────────────────────
function drainQueue() {
  const nextItems = batchQueue.filter(q => q.status === 'queued');
  const slots = MAX_CONCURRENCY - activeCount;
  nextItems.slice(0, slots).forEach(processItem);
}

async function processItem(item) {
  item.status = 'running';
  activeCount++;
  renderQueueItem(item);

  try {
    // POST /upload
    const doc = await uploadDocument(item.file);
    item.docId = doc.id ?? doc.document_id;
    renderQueueItem(item, 'Uploaded, analyzing…');

    // POST /analyze
    const job = await startAnalysis(item.docId);

    // GET /analysis/{id}
    const results = await getAnalysisResults(job.job_id);
    item.result = results;
    item.status = 'done';

    // Persist to history
    addToHistory(doc, results);
  } catch (err) {
    item.status = 'error';
    item.error = err.message;
  }

  activeCount--;
  renderQueueItem(item);
  updateBatchSummary();

  // Process next in queue
  drainQueue();

  // Final toast when all done
  const remaining = batchQueue.filter(q => q.status === 'queued' || q.status === 'running');
  if (remaining.length === 0) {
    const done   = batchQueue.filter(q => q.status === 'done').length;
    const errors = batchQueue.filter(q => q.status === 'error').length;
    toast(`Batch complete: ${done} analysed, ${errors} failed.`, errors > 0 ? 'warn' : 'success');
  }
}

// ── Render ─────────────────────────────────────────────────────
function renderQueue() {
  const grid   = $('batchGrid');
  const dzWrap = $('batchDropWrap');
  if (!grid) return;

  if (!batchQueue.length) {
    grid.innerHTML = '';
    dzWrap?.classList.remove('hidden');
    return;
  }
  dzWrap?.classList.add('hidden');

  grid.innerHTML = batchQueue.map(item => renderItemHTML(item)).join('');
  wireItemRemove();
}

function renderQueueItem(item, subLabel = '') {
  const el = document.getElementById(`bqi_${item.id}`);
  if (!el) return;
  el.outerHTML = renderItemHTML(item, subLabel);
  wireItemRemove();
}

function renderItemHTML(item, subLabel = '') {
  const ext = item.file.name.split('.').pop().toUpperCase();
  const statusConfig = {
    pending: { icon: '○', cls: 'pending', label: 'Pending' },
    queued:  { icon: '…', cls: 'queued',  label: 'Queued'  },
    running: { icon: '▶', cls: 'running',  label: subLabel || 'Analysing…' },
    done:    { icon: '✓', cls: 'done',    label: `Score: ${item.result?.score ?? '?'}%` },
    error:   { icon: '✕', cls: 'error',   label: item.error ?? 'Failed' },
  };
  const sc = statusConfig[item.status] || statusConfig.pending;
  const risk = item.result?.classification ?? '';
  const riskCls = risk === 'HIGH_RISK' ? 'high' : risk === 'SUSPICIOUS' ? 'med' : risk ? 'low' : '';
  const riskLabel = risk.replace('_', ' ');

  return `
    <div class="batch-item ${sc.cls}" id="bqi_${item.id}">
      <div class="bi-ext">${ext}</div>
      <div class="bi-name" title="${item.file.name}">${item.file.name}</div>
      <div class="bi-size">${fmtBytes(item.file.size)}</div>
      ${item.status === 'running' ? `<div class="bi-progbar"><div class="bi-progfill"></div></div>` : ''}
      <div class="bi-status-row">
        <span class="bi-status-icon ${sc.cls}">${sc.icon}</span>
        <span class="bi-status-lbl">${sc.label}</span>
        ${riskCls ? `<span class="bi-risk ${riskCls}">${riskLabel}</span>` : ''}
      </div>
      ${item.status === 'pending' || item.status === 'error'
        ? `<button class="bi-remove" data-id="${item.id}" title="Remove item" aria-label="Remove ${item.file.name}">×</button>` : ''
      }
    </div>
  `;
}

function wireItemRemove() {
  document.querySelectorAll('.bi-remove').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      batchQueue = batchQueue.filter(q => q.id !== btn.dataset.id);
      renderQueue();
      updateBatchControls();
    });
  });
}

function updateBatchControls() {
  const runBtn   = $('batchRunBtn');
  const clearBtn = $('batchClearBtn');
  const hasPending = batchQueue.some(q => q.status === 'pending' || q.status === 'error');
  const hasActive  = batchQueue.some(q => q.status === 'running' || q.status === 'queued');
  if (runBtn) {
    runBtn.disabled = !hasPending || hasActive;
    runBtn.textContent = hasActive ? 'Processing…' : `Run Batch (${batchQueue.filter(q => q.status === 'pending' || q.status === 'error').length})`;
  }
  if (clearBtn) clearBtn.disabled = hasActive;

  const queueCount = $('batchQueueCount');
  if (queueCount) queueCount.textContent = `${batchQueue.length} document${batchQueue.length !== 1 ? 's' : ''}`;
}

function updateBatchSummary() {
  const done   = batchQueue.filter(q => q.status === 'done').length;
  const errors = batchQueue.filter(q => q.status === 'error').length;
  const totalEl = $('batchDoneCount');
  const errEl   = $('batchErrCount');
  if (totalEl) totalEl.textContent = done;
  if (errEl)   errEl.textContent   = errors;
  updateBatchControls();
}
