/**
 * history.js — Analysis History Dashboard
 *
 * Renders a paginated, filterable table of past document
 * analyses stored in localStorage (or fetched from the backend).
 */

import { $, $$, fmtDateTime, SEV_CLASS } from './utils.js';
import { appState } from './state.js';
import { navigateTo } from './router.js';

// ── Local history store (persisted in localStorage) ────────────
const STORAGE_KEY = 'forensica_history';

/** Add a completed analysis to the local history store */
export function addToHistory(doc, results) {
  const items = loadHistory();
  items.unshift({
    id: doc.id ?? doc.document_id,
    filename: doc.filename,
    size_bytes: doc.size_bytes,
    uploaded_at: doc.uploaded_at ?? new Date().toISOString(),
    score: results.score,
    classification: results.classification,
    anomalies: results.anomalies?.length ?? 0,
    completed_at: new Date().toISOString(),
  });
  // Keep at most 50 items
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(0, 50)));
}

function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch {
    return [];
  }
}

// ── Page entry ─────────────────────────────────────────────────
export function onHistoryPageEnter() {
  renderHistory();
  wireHistoryControls();
}

// ── Render ─────────────────────────────────────────────────────
function renderHistory(filter = '') {
  const list = $('historyList');
  const empty = $('historyEmpty');
  const countEl = $('historyCount');
  if (!list) return;

  let items = loadHistory();
  if (filter) {
    items = items.filter(i =>
      i.filename.toLowerCase().includes(filter.toLowerCase()) ||
      i.classification.toLowerCase().includes(filter.toLowerCase())
    );
  }

  if (countEl) countEl.textContent = `${items.length} record${items.length !== 1 ? 's' : ''}`;

  if (!items.length) {
    list.innerHTML = '';
    empty?.classList.remove('hidden');
    return;
  }
  empty?.classList.add('hidden');

  list.innerHTML = items.map((item, idx) => {
    const cls = item.classification === 'HIGH_RISK' ? 'high' : item.classification === 'SUSPICIOUS' ? 'med' : 'low';
    const label = item.classification.replace('_', ' ');
    const riskIcon = cls === 'high' ? '⚠' : cls === 'med' ? '⚡' : '✓';
    const scoreColor = item.score >= 70 ? 'var(--red)' : item.score >= 50 ? 'var(--orange)' : 'var(--green)';
    return `
      <div class="history-row" data-idx="${idx}" tabindex="0" aria-label="View analysis for ${item.filename}">
        <div class="hr-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
        </div>
        <div class="hr-main">
          <div class="hr-filename">${item.filename}</div>
          <div class="hr-meta">${fmtDateTime(item.completed_at)} &middot; ${item.anomalies} anomaly${item.anomalies !== 1 ? 's' : ''}</div>
        </div>
        <div class="hr-score" style="color:${scoreColor}; font-variant-numeric:tabular-nums">${item.score}%</div>
        <div class="hr-risk ${cls}">${riskIcon} ${label}</div>
        <button class="hr-view btn-ghost" data-idx="${idx}" title="View analysis">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        </button>
      </div>
    `;
  }).join('');

  // Wire row clicks
  list.querySelectorAll('.hr-view').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const item = loadHistory()[parseInt(btn.dataset.idx)];
      if (item) viewHistoryItem(item);
    });
  });
  list.querySelectorAll('.history-row').forEach(row => {
    row.addEventListener('click', () => {
      const item = loadHistory()[parseInt(row.dataset.idx)];
      if (item) viewHistoryItem(item);
    });
    row.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        const item = loadHistory()[parseInt(row.dataset.idx)];
        if (item) viewHistoryItem(item);
      }
    });
  });
}

function viewHistoryItem(item) {
  // Restore results into state so the Results page can render
  import('./state.js').then(({ setState }) => {
    import('./results.js').then(({ renderResults }) => {
      const fakeResults = {
        score: item.score,
        classification: item.classification,
        anomalies: [],
        module_scores: {},
        overlays: [],
        completed_at: item.completed_at,
      };
      setState({ results: fakeResults, document: { id: item.id, filename: item.filename, size_bytes: item.size_bytes, uploaded_at: item.uploaded_at } });
      renderResults(fakeResults);
      navigateTo('results');
    });
  });
}

function wireHistoryControls() {
  const searchInput = $('historySearch');
  const clearBtn    = $('historyClear');

  searchInput?.addEventListener('input', (e) => renderHistory(e.target.value));
  clearBtn?.addEventListener('click', () => {
    if (confirm('Clear all analysis history? This cannot be undone.')) {
      localStorage.removeItem(STORAGE_KEY);
      renderHistory();
    }
  });
}
