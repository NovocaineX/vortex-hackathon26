/**
 * router.js — SPA Navigation Router
 *
 * Central routing layer. Each page has an enter/exit lifecycle.
 * Modules register themselves here; router dispatches on navigate.
 */

import { $, $$ } from './utils.js';
import { appState, setState } from './state.js';

// Lazy-imported page handlers
let _onResultsEnter = null;
let _onReportEnter  = null;

export function registerHandlers({ onResultsPageEnter, onReportPageEnter }) {
  _onResultsEnter = onResultsPageEnter;
  _onReportEnter  = onReportPageEnter;
}

// Page ID map
const PAGE_MAP = {
  home:     'pageHome',
  upload:   'pageUpload',
  results:  'pageResults',
  report:   'pageReport',
  settings: 'pageHome',   // fallback for now
};

// Nav links that highlight for each page
const NAV_ALIAS = {
  results:  'upload',   // "Analysis" nav tab covers both upload + results
  settings: 'home',
};

export function navigateTo(page) {
  // Hide all pages
  document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));

  // Show target
  const targetId = PAGE_MAP[page] || 'pageHome';
  const targetEl = $(targetId);
  if (targetEl) targetEl.classList.remove('hidden');

  // Active nav state
  const navKey = NAV_ALIAS[page] || page;
  $$('.nav-link').forEach(l => l.classList.toggle('active', l.dataset.page === navKey));
  $$('.sidebar-item').forEach(b => b.classList.toggle('active', b.dataset.page === page));

  setState({ currentPage: page });

  // Page lifecycle hooks
  if (page === 'results' && _onResultsEnter) _onResultsEnter();
  if (page === 'report'  && _onReportEnter)  _onReportEnter();

  // Scroll to top
  $('mainContent')?.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Wire all navigation elements ──────────────────────────────
export function initRouter() {
  document.querySelectorAll('[data-page]').forEach(el => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      navigateTo(el.dataset.page);
    });
  });

  // Logo click → home
  $('logoHome')?.addEventListener('click', () => navigateTo('home'));

  // Keyboard shortcuts: Ctrl+1–4
  document.addEventListener('keydown', (e) => {
    if (!e.ctrlKey && !e.metaKey) return;
    const map = { '1': 'home', '2': 'upload', '3': 'results', '4': 'report' };
    if (map[e.key]) { e.preventDefault(); navigateTo(map[e.key]); }
  });

  // Sidebar toggle
  $('sidebarToggle')?.addEventListener('click', () => {
    const sidebar = $('sidebar');
    if (!sidebar) return;
    const isMobile = window.innerWidth <= 960;
    if (isMobile) {
      sidebar.classList.toggle('mobile-open');
    } else {
      sidebar.classList.toggle('collapsed');
    }
  });
}
