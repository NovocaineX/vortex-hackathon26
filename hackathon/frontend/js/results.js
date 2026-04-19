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
import { getPreviewUrl } from './api.js';

let radarChartInst = null;

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

  // Render actual document image behind overlays
  const docId = appState.document?.id ?? appState.document?.document_id;
  const previewUrl = docId ? getPreviewUrl(docId) : null;
  const container = $('resSimDoc');

  if (previewUrl && container) {
    let previewImg = $('resPreviewImg');
    if (!previewImg) {
      previewImg = document.createElement('img');
      previewImg.id = 'resPreviewImg';
      previewImg.alt = 'Document Preview';
      previewImg.style.cssText = 'width:100%;height:100%;object-fit:contain;border-radius:4px;display:block;';
      container.insertBefore(previewImg, container.firstChild);
    }

    previewImg.onerror = () => {
      previewImg.style.display = 'none';
      container.querySelectorAll('.sim-header,.sim-body,.sim-footer').forEach(el => el.style.display = '');
    };

    previewImg.src = previewUrl;
    previewImg.style.display = 'block';
    container.style.cssText = 'position:relative;background:transparent;padding:0;border-radius:4px;overflow:hidden;';
    container.querySelectorAll('.sim-header,.sim-body,.sim-footer').forEach(el => el.style.display = 'none');
  }
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
  const container = document.getElementById('resultsScoreBars');
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

  // Plot Radar Chart
  const canvas = document.getElementById('moduleRadarChart');
  if (canvas && window.Chart) {
    if (radarChartInst) radarChartInst.destroy();
    
    const labels = entries.map(([k]) => shortNames[k] ?? k);
    const dataVals = entries.map(([, v]) => v * 100);

    radarChartInst = new Chart(canvas, {
      type: 'radar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Anomaly Confidence (%)',
          data: dataVals,
          backgroundColor: 'rgba(10, 168, 158, 0.25)',
          borderColor: 'rgba(10, 168, 158, 1)',
          pointBackgroundColor: 'rgba(6, 103, 208, 1)',
          borderWidth: 2,
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false }
        },
        scales: {
          r: {
            angleLines: { color: 'rgba(255, 255, 255, 0.1)' },
            grid: { color: 'rgba(255, 255, 255, 0.15)' },
            pointLabels: { color: 'var(--text-secondary)', font: { size: 10 } },
            ticks: { display: false, min: 0, max: 100 }
          }
        }
      }
    });
  }
}

function renderAnomalyList(anomalies) {
  const list = $('anomalyList');
  if (!list) return;

  // Clear any existing generic template elements
  list.innerHTML = '';

  if (!anomalies?.length) {
    list.innerHTML = `
      <div class="anomaly-empty" style="text-align:center; padding:3rem 1rem; color:var(--text-muted); display:flex; flex-direction:column; align-items:center; gap:0.5rem;">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2" style="opacity:0.8;">
          <circle cx="12" cy="12" r="10"/><path d="M9 12l2 2 4-4"/>
        </svg>
        <div style="font-weight:500; color:var(--text-primary); margin-top:0.5rem;">No Anomalies Detected</div>
        <div style="font-size:0.85rem;">Document passed automated forensic sweep</div>
      </div>
    `;
    return;
  }

  list.innerHTML = anomalies.map((a, i) => `
    <div class="anomaly-item ${i === 0 ? 'active' : ''}" data-anomaly-id="${a.id}" data-index="${i}">
      <div class="anomaly-header-row">
        <span class="anomaly-sev ${SEV_CLASS[a.severity] ?? 'low'}">${a.severity}</span>
        <span class="anomaly-type">${(a.label || a.type || 'Anomaly').replace(/_/g, ' ')}</span>
        <span class="anomaly-conf">${pct(a.confidence)}</span>
      </div>
      <p class="anomaly-desc">${a.description}</p>
      <div class="anomaly-region">${a.region ? `Region: (${a.region.x},${a.region.y}) → (${a.region.x+(a.region.width ?? a.region.w)},${a.region.y+(a.region.height ?? a.region.h)})` : 'Region: Global'}</div>
    </div>
  `).join('');
}

function renderOverlays(overlays) {
  const container = $('resSimDoc');
  if (!container) return;

  // Remove old dynamic overlays
  container.querySelectorAll('.dyn-overlay').forEach(el => el.remove());

  if (!overlays?.length) return;

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
