/**
 * results.js — Analysis Results Panel Module
 *
 * Renders the results page from data returned by GET /analysis/{id}.
 * Manages anomaly list interactions, document viewer overlays,
 * and zoom/pan controls.
 */

import { appState, setViewerState } from './state.js';
import { $, pct, animateCounter, SEV_CLASS, toast } from './utils.js';
import { navigateTo } from './router.js';

// ── Public: called after analysis completes ────────────────────
export function renderResults(data) {
  if (!data) return;

  // Populate score ring (animated on page visit)
  if ($('resultScore')) $('resultScore').textContent = data.score + '%';

  // Risk badge
  updateRiskBadge(data.classification);

  // Breakdown bars
  renderModuleBars(data.module_scores);

  // Anomaly list
  renderAnomalyList(data.anomalies);

  // Overlay boxes in doc viewer
  renderOverlays(data.overlays);

  // Anomaly count badge
  if ($('anomalyCount')) $('anomalyCount').textContent = `${data.anomalies.length} Found`;
  if ($('resultsFileName')) $('resultsFileName').textContent = appState.document?.filename ?? 'document.pdf';
}

// ── Called on page navigation to Results ──────────────────────
export function onResultsPageEnter() {
  const data = appState.results;
  if (!data) {
    // No results yet — show placeholder
    return;
  }

  renderResults(data);

  // Animate ring
  const ring = $('resultRingFg');
  if (ring) {
    const circ   = 2 * Math.PI * 68;
    const offset = circ * (1 - data.score / 100);
    ring.style.strokeDasharray  = circ;
    ring.style.strokeDashoffset = circ;
    requestAnimationFrame(() => {
      setTimeout(() => { ring.style.strokeDashoffset = offset; }, 80);
    });
  }

  // Animate score counter
  const scoreEl = $('resultScore');
  if (scoreEl) animateCounter(scoreEl, data.score, 900, '%');

  // Animate breakdown bars
  document.querySelectorAll('.bb-fill').forEach(bar => {
    const w = bar.style.width;
    bar.style.width = '0%';
    setTimeout(() => { bar.style.width = w; }, 200);
  });

  // Wire anomaly click interactions
  wireAnomalyClicks();
  initResultsViewer();
}

// ── Render helpers ─────────────────────────────────────────────
function updateRiskBadge(classification) {
  const badge = $('riskBadge');
  if (!badge) return;
  const cls = classification === 'HIGH_RISK' ? 'high' : classification === 'SUSPICIOUS' ? 'med' : 'low';
  const label = classification.replace('_', ' ');
  badge.className = `risk-classification ${cls}`;
  badge.innerHTML = `<span class="risk-icon">${cls === 'high' ? '⚠' : cls === 'med' ? '⚡' : '✓'}</span> ${label}`;
}

function renderModuleBars(scores) {
  if (!scores) return;
  const container = document.querySelector('.score-breakdown');
  if (!container) return;

  const entries = Object.entries(scores);
  const shortNames = { font_detector: 'Font', layout_checker: 'Layout', pixel_analyzer: 'Pixel', ocr_extractor: 'OCR', compression_check: 'Comp.' };
  const colorMap = (v) => v >= 0.7 ? 'red' : v >= 0.5 ? 'orange' : 'yellow';

  container.innerHTML = entries.map(([key, val]) => `
    <div class="breakdown-bar">
      <span class="bb-label">${shortNames[key] ?? key}</span>
      <div class="bb-track"><div class="bb-fill ${colorMap(val)}" style="width:${Math.round(val*100)}%"></div></div>
      <span class="bb-val">${Math.round(val*100)}%</span>
    </div>
  `).join('');
}

function renderAnomalyList(anomalies) {
  const list = $('anomalyList');
  if (!list || !anomalies?.length) return;

  list.innerHTML = anomalies.map((a, i) => `
    <div class="anomaly-item ${i === 0 ? 'active' : ''}" data-anomaly-id="${a.id}" data-index="${i}">
      <div class="anomaly-header-row">
        <span class="anomaly-sev ${SEV_CLASS[a.severity] ?? 'low'}">${a.severity}</span>
        <span class="anomaly-type">${a.label}</span>
        <span class="anomaly-conf">${pct(a.confidence)}</span>
      </div>
      <p class="anomaly-desc">${a.description}</p>
      <div class="anomaly-region">${a.region ? `Region: (${a.region.x},${a.region.y}) → (${a.region.x+a.region.w},${a.region.y+a.region.h})` : 'Region: Global'}</div>
    </div>
  `).join('');
}

function renderOverlays(overlays) {
  if (!overlays?.length) return;
  const container = $('resSimDoc');
  if (!container) return;

  // Remove old dynamic overlays
  container.querySelectorAll('.dyn-overlay').forEach(el => el.remove());

  overlays.forEach(ov => {
    const div = document.createElement('div');
    div.className = `overlay-box ${ov.color} dyn-overlay`;
    div.id = `resOv_${ov.id}`;
    div.style.cssText = `top:${ov.y};left:${ov.x};width:${ov.w};height:${ov.h}`;
    div.innerHTML = `<div class="overlay-label">${ov.label}</div>`;
    container.appendChild(div);
  });
}

// ── Anomaly click → highlight overlay ─────────────────────────
function wireAnomalyClicks() {
  document.querySelectorAll('#anomalyList .anomaly-item').forEach((item) => {
    item.addEventListener('click', () => {
      document.querySelectorAll('#anomalyList .anomaly-item').forEach(a => a.classList.remove('active'));
      item.classList.add('active');

      const anomalyId = item.dataset.anomalyId;
      setViewerState({ focusedAnomalyId: anomalyId });

      // Pulse the overlay
      const ov = document.getElementById(`resOv_${anomalyId}`);
      if (ov) {
        ov.style.animation = 'none';
        requestAnimationFrame(() => { ov.style.animation = ''; });
      }
    });
  });
}

// ── Results viewer zoom / overlay toggles ─────────────────────
function initResultsViewer() {
  let zoom = 100;
  const update = () => { if ($('resZoomLevel')) $('resZoomLevel').textContent = zoom + '%'; };

  $('resZoomIn')?.addEventListener('click',  () => { zoom = Math.min(zoom + 15, 200); update(); });
  $('resZoomOut')?.addEventListener('click', () => { zoom = Math.max(zoom - 15,  40); update(); });

  $('resBBox')?.addEventListener('change', (e) => {
    document.querySelectorAll('.dyn-overlay').forEach(el => {
      el.style.display = e.target.checked ? 'block' : 'none';
    });
    setViewerState({ showBoundingBoxes: e.target.checked });
  });

  $('resHeat')?.addEventListener('change', (e) => {
    $('heatmapLayer')?.classList.toggle('hidden', !e.target.checked);
    setViewerState({ showHeatmap: e.target.checked });
  });
}
