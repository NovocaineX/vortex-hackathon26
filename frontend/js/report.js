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

  const docId = appState.document?.id ?? 'demo';
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
  if (!anomalies?.length) return;
  const body = document.querySelector('.report-anomaly-table');
  if (!body) return;

  const header = body.querySelector('.rat-header');
  const rows = anomalies.map((a, i) => `
    <div class="rat-row">
      <span class="rat-num">${String(i+1).padStart(2,'0')}</span>
      <span class="rat-type">${a.type}</span>
      <span class="rat-sev ${a.severity === 'HIGH' ? 'high-text' : a.severity === 'MEDIUM' ? 'med-text' : 'low-text'}">${a.severity}</span>
      <span class="rat-conf">${pct(a.confidence)}</span>
      <span class="rat-loc mono">${a.region}</span>
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
    const report  = appState.report;
    const url     = report?.download_url;

    toast('Generating PDF report… (GET /report/{id}/download)', 'info');

    if (url && url !== '#' && !url.startsWith('/report/')) {
      window.open(url, '_blank');
    } else {
      setTimeout(() => {
        toast('PDF download requires backend integration. Report data is ready.', 'success');
      }, 1200);
    }
  });
}
