/**
 * report.js — Verification Report Module
 *
 * Renders the report page from data returned by GET /report/{id}.
 * Handles the download action and dynamic field population.
 */

import { getReport } from './api.js';
import { appState, setState } from './state.js';
import { $, fmtBytes, fmtDate, fmtDateTime, pct, toast } from './utils.js';

// ── Called when user navigates to the Report page ─────────────
export async function onReportPageEnter() {
  populateStaticFields();

  // Use cached report if available, otherwise fetch
  if (appState.report) {
    renderReport(appState.report);
    return;
  }

  const docId = appState.results?.analysis_id ?? appState.document?.document_id ?? appState.document?.id ?? 'demo';
  try {
    const report = await getReport(docId);
    setState({ report });
    renderReport(report);
  } catch (err) {
    toast(`Could not load report: ${err.message}`, 'error');
  }
}

// ── Render ─────────────────────────────────────────────────────
function renderReport(report) {
  // Metadata
  if ($('reportId'))      $('reportId').textContent      = report.report_id;
  if ($('reportDate'))    $('reportDate').textContent    = fmtDateTime(report.generated_at);
  if ($('rptUploadDate')) $('rptUploadDate').textContent = fmtDate(report.generated_at);
  if ($('rptFileName'))   $('rptFileName').textContent   = report.document_info?.filename ?? '—';
  if ($('rptDocType'))    $('rptDocType').textContent    = report.document_info?.type ?? 'Document';
  if ($('rptFileSize'))   $('rptFileSize').textContent   = fmtBytes(report.document_info?.size_bytes ?? 0);
  if ($('rptPages'))      $('rptPages').textContent      = `${report.document_info?.pages ?? 1} page`;

  // Verdict block
  renderVerdict(report.verdict);

  // Anomaly table
  renderAnomalyTable(report.anomalies);

  // Module scores
  renderModuleScores(report.module_scores);

  // Animate score bars
  animateBars();
}

function populateStaticFields() {
  const now = new Date();
  if ($('reportDate'))    $('reportDate').textContent    = fmtDateTime(now.toISOString());
  if ($('rptUploadDate')) $('rptUploadDate').textContent = fmtDate(now.toISOString());
  // If we already have document info from state, populate it
  const doc = appState.document;
  if (doc) {
    if ($('rptFileName')) $('rptFileName').textContent = doc.filename;
    if ($('rptFileSize')) $('rptFileSize').textContent = fmtBytes(doc.size_bytes ?? 0);
  }
}

function renderVerdict(verdict) {
  if (!verdict) return;
  const block = document.querySelector('.verdict-block');
  if (!block) return;

  const cls   = verdict.classification === 'HIGH_RISK' ? 'high' : verdict.classification === 'SUSPICIOUS' ? 'med' : 'low';
  const icon  = cls === 'high' ? '⚠' : cls === 'med' ? '⚡' : '✓';
  const label = verdict.classification.replace('_', ' ');

  block.className = `verdict-block ${cls}`;
  const titleEl = block.querySelector('.verdict-title');
  const subEl   = block.querySelector('.verdict-sub');
  const iconEl  = block.querySelector('.verdict-icon');
  if (titleEl) titleEl.textContent = `${label} — Document Likely ${cls === 'low' ? 'Authentic' : 'Forged'}`;
  if (subEl)   subEl.innerHTML     = `Forgery confidence score: <strong>${verdict.score}%</strong>. ${verdict.recommendation}`;
  if (iconEl)  iconEl.textContent  = icon;
}

function renderAnomalyTable(anomalies) {
  const body = document.querySelector('.report-anomaly-table');
  if (!body) return;

  const header = body.querySelector('.rat-header');

  if (!anomalies?.length) {
    body.innerHTML = (header?.outerHTML ?? '') + `
      <div class="rat-row" style="display: flex; justify-content: center; padding: 2rem; color: var(--text-muted);">
        No anomalies detected in this document.
      </div>
    `;
    return;
  }

  const formatRegion = (r) => {
    if (!r) return 'Global';
    if (typeof r === 'string') return r;
    return `(${Math.round(r.x)},${Math.round(r.y)})&rarr;(${Math.round(r.x+(r.width??r.w))},${Math.round(r.y+(r.height??r.h))})`;
  };

  const rows = anomalies.map((a, i) => `
    <div class="rat-row">
      <span class="rat-num">${String(i+1).padStart(2,'0')}</span>
      <span class="rat-type">${(a.type || a.label || 'Anomaly').replace(/_/g, ' ')}</span>
      <span class="rat-sev ${a.severity === 'HIGH' ? 'high-text' : a.severity === 'MEDIUM' ? 'med-text' : 'low-text'}">${a.severity || 'LOW'}</span>
      <span class="rat-conf">${pct(a.confidence)}</span>
      <span class="rat-loc mono">${formatRegion(a.region)}</span>
    </div>
  `).join('');

  body.innerHTML = (header?.outerHTML ?? '') + rows;
}

function renderModuleScores(scores) {
  if (!scores) return;
  const container = document.querySelector('.module-scores');
  if (!container) return;

  const colorMap = (v) => v >= 0.7 ? 'red' : v >= 0.5 ? 'orange' : 'yellow';

  container.innerHTML = Object.entries(scores).map(([label, val]) => `
    <div class="ms-row">
      <span class="ms-lbl">${label}</span>
      <div class="ms-track"><div class="ms-fill ${colorMap(val)}" data-target="${Math.round(val*100)}" style="width:0%"></div></div>
      <span class="ms-val">${Math.round(val*100)}%</span>
    </div>
  `).join('');

  animateBars();
}

function animateBars() {
  document.querySelectorAll('.ms-fill[data-target]').forEach(bar => {
    const target = bar.dataset.target + '%';
    bar.style.width = '0%';
    setTimeout(() => { bar.style.width = target; }, 150);
  });
}

// ── Download handler ───────────────────────────────────────────
export function initReport() {
  $('downloadReportBtn')?.addEventListener('click', async () => {
    const report = appState.report;
    const url    = report?.download_url;

    if (url && url !== '#' && !url.startsWith('/report/')) {
      // Real backend URL — open directly
      toast('Opening PDF download…', 'info');
      window.open(url, '_blank');
    } else {
      // No backend PDF yet — print the current page as PDF via browser
      toast('Opening print dialog — save as PDF to download the report.', 'info', 3000);
      setTimeout(() => window.print(), 600);
    }
  });

  const editBtn = $('editDocTypeBtn');
  const typeVal = $('rptDocType');
  if (editBtn && typeVal) {
    editBtn.addEventListener('click', () => {
      // Toggle edit mode
      if (typeVal.querySelector('input')) {
        const input = typeVal.querySelector('input');
        typeVal.textContent = input.value || 'Document';
        editBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>';
      } else {
        const curr = typeVal.textContent;
        typeVal.innerHTML = `<input type="text" id="docTypeInput" value="${curr}" style="background:var(--bg-layer); color:var(--text-primary); border:1px solid var(--border); padding:4px 8px; border-radius:4px; font-size:0.85rem; width:100%; font-family:inherit;" />`;
        editBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>'; // checkmark
        document.getElementById('docTypeInput').focus();
      }
    });
  }
}
