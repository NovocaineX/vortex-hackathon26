/**
 * app.js — Forensica AI Application Entry Point
 *
 * Bootstraps all modules, wires them together, and starts the app.
 * This is the ONLY script tag loaded in index.html (as type="module").
 */

import { initRouter, navigateTo, registerHandlers } from './router.js';
import { initUpload, initUploadViewer }              from './upload.js';
import { onResultsPageEnter }                        from './results.js';
import { onReportPageEnter, initReport }             from './report.js';
import { toast }                                     from './utils.js';
import { $, $$ }                                     from './utils.js';
import { checkBackendHealth }                        from './api.js';

// ── Bootstrap ──────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', async () => {
  // Auto-detect backend — switches API client to live mode if reachable
  const backendLive = await checkBackendHealth();

  // Register page lifecycle handlers with the router
  registerHandlers({ onResultsPageEnter, onReportPageEnter });

  // Initialize all modules
  initRouter();
  initUpload();
  initUploadViewer();
  initReport();

  // Home page CTA buttons
  $('heroStartBtn')?.addEventListener('click', () => navigateTo('upload'));
  $('fmtUploadBtn')?.addEventListener('click', () => navigateTo('upload'));
  $('heroLearnBtn')?.addEventListener('click', () => {
    document.querySelector('.pipeline-grid')?.scrollIntoView({ behavior: 'smooth' });
  });
  $('goReportBtn')?.addEventListener('click', () => navigateTo('report'));
  $('newAnalysisBtn')?.addEventListener('click', () => navigateTo('upload'));

  // Start on home
  navigateTo('home');

  // Kick off background effects
  startParticleCanvas();
  animateHeroRing();

  toast(
    backendLive
      ? 'Forensica AI connected to live backend. Upload a document to begin.'
      : 'Forensica AI ready (mock mode). Upload a document to begin.',
    backendLive ? 'success' : 'info',
    4500,
  );
});

// ── Particle background ────────────────────────────────────────
function startParticleCanvas() {
  const canvas = document.createElement('canvas');
  canvas.id = 'bgCanvas';
  canvas.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:0;opacity:0.15;';
  document.body.prepend(canvas);

  const ctx = canvas.getContext('2d');
  let W, H;
  const resize = () => { W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; };
  resize();
  window.addEventListener('resize', resize);

  const N = 55;
  const pts = Array.from({ length: N }, () => ({
    x: Math.random() * window.innerWidth,
    y: Math.random() * window.innerHeight,
    r: Math.random() * 1.4 + 0.3,
    vx: (Math.random() - 0.5) * 0.28,
    vy: (Math.random() - 0.5) * 0.28,
  }));

  const frame = () => {
    ctx.clearRect(0, 0, W, H);
    pts.forEach(p => {
      p.x = (p.x + p.vx + W) % W;
      p.y = (p.y + p.vy + H) % H;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = '#0aa89e';
      ctx.fill();
    });
    for (let i = 0; i < N; i++) {
      for (let j = i + 1; j < N; j++) {
        const dx = pts[i].x - pts[j].x, dy = pts[i].y - pts[j].y;
        const d  = Math.sqrt(dx * dx + dy * dy);
        if (d < 110) {
          ctx.beginPath();
          ctx.moveTo(pts[i].x, pts[i].y);
          ctx.lineTo(pts[j].x, pts[j].y);
          ctx.strokeStyle = `rgba(10,168,158,${0.11 * (1 - d / 110)})`;
          ctx.lineWidth = 0.45;
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(frame);
  };
  frame();
}

// ── Hero ring animation ────────────────────────────────────────
function animateHeroRing() {
  const ring = $('homeRingFg');
  if (!ring) return;
  ring.style.strokeDashoffset = 314;
  setTimeout(() => { ring.style.strokeDashoffset = 94; }, 700);
}
