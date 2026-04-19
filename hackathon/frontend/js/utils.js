/**
 * utils.js — Shared UI utilities
 */

// ── DOM shorthand ──────────────────────────────────────────────
export const $ = (id) => document.getElementById(id);
export const $$ = (sel) => document.querySelectorAll(sel);

// ── Format bytes ───────────────────────────────────────────────
export function fmtBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1_048_576).toFixed(1)} MB`;
}

// ── Format date ────────────────────────────────────────────────
export function fmtDate(isoStr) {
  const d = new Date(isoStr);
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

export function fmtDateTime(isoStr) {
  const d = new Date(isoStr);
  return fmtDate(isoStr) + ', ' + d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

// ── Confidence → percentage string ────────────────────────────
export function pct(confidence) {
  return Math.round(confidence * 100) + '%';
}

// ── Toast notification system ──────────────────────────────────
const TOAST_ICONS = {
  success: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>`,
  error:   `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
  info:    `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
  warn:    `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
};
const TOAST_COLORS = { success: 'var(--green)', error: 'var(--red)', info: 'var(--teal)', warn: 'var(--orange)' };

export function toast(message, type = 'info', duration = 3500) {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `
    <span class="toast-icon" style="color:${TOAST_COLORS[type]}">${TOAST_ICONS[type]}</span>
    <span class="toast-msg">${message}</span>
    <button class="toast-close" onclick="this.parentElement.remove()">×</button>
  `;
  container.appendChild(el);
  setTimeout(() => {
    el.style.animation = 'toastOut .3s ease forwards';
    setTimeout(() => el.remove(), 300);
  }, duration);

  // Send to persistent sidebar
  addNotification(message, type);
}

export function addNotification(message, type = 'info') {
  const list = document.getElementById('notifList');
  const empty = document.getElementById('notifEmpty');
  if (!list) return;
  if (empty) empty.style.display = 'none';

  const item = document.createElement('div');
  item.className = `notif-sidebar-item ${type}`;
  const now = new Date();
  const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  item.innerHTML = `
    <div class="notif-sidebar-icon" style="color:${TOAST_COLORS[type]}">${TOAST_ICONS[type]}</div>
    <div class="notif-sidebar-content">
      <div class="notif-sidebar-msg">${message}</div>
      <div class="notif-sidebar-time">${timeStr}</div>
    </div>
  `;
  list.prepend(item);
  incrementNotifBadge();
}

export function initNotificationSidebar() {
  const btn = document.getElementById('notifBtn');
  const closeBtn = document.getElementById('closeNotifBtn');
  const sidebar = document.getElementById('notifSidebar');
  
  if (btn && sidebar) {
    btn.addEventListener('click', () => {
      sidebar.classList.toggle('open');
      resetNotifBadge(); // clear badge counter when opened
    });
  }
  if (closeBtn && sidebar) {
    closeBtn.addEventListener('click', () => {
      sidebar.classList.remove('open');
    });
  }
}

// ── Animate a counter ──────────────────────────────────────────
export function animateCounter(el, target, duration = 1100, suffix = '%') {
  const t0 = performance.now();
  const step = (now) => {
    const p = Math.min((now - t0) / duration, 1);
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(target * eased) + suffix;
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// ── Severity color mapping ─────────────────────────────────────
export const SEV_CLASS = { HIGH: 'high', MEDIUM: 'med', LOW: 'low' };
export const SEV_COLOR = {
  HIGH:   'var(--red)',
  MEDIUM: 'var(--orange)',
  LOW:    'var(--green)',
};

// ── Notification badge counter ─────────────────────────────────
let _notifCount = 0;

export function incrementNotifBadge() {
  _notifCount++;
  const badge = document.querySelector('#notifBtn .notif-badge');
  if (!badge) return;
  badge.textContent = _notifCount;
  badge.style.display = 'flex';
  badge.classList.remove('notif-pulse');
  // Force reflow then re-add animation
  void badge.offsetWidth;
  badge.classList.add('notif-pulse');
}

export function resetNotifBadge() {
  _notifCount = 0;
  const badge = document.querySelector('#notifBtn .notif-badge');
  if (badge) badge.style.display = 'none';
}

