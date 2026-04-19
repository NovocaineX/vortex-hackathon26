/**
 * auth.js — Firebase Google Authentication
 *
 * Wraps Firebase Auth v10 Modular SDK.
 * Falls back to a demo sign-in flow when Firebase config is absent
 * (suitable for hackathon demo without a real Firebase project).
 */

// ── Firebase config ────────────────────────────────────────────
// Paste your Firebase Web SDK config here to enable real auth.
// Leave empty to use the demo/mock flow (works offline).
const FIREBASE_CONFIG = {
  // apiKey: "",
  // authDomain: "",
  // projectId: "",
  // storageBucket: "",
  // messagingSenderId: "",
  // appId: "",
};

const HAS_REAL_CONFIG = Object.values(FIREBASE_CONFIG).some(v => v && v.length > 0);

// ── Auth state ─────────────────────────────────────────────────
export let currentUser = null;
const authListeners = [];

export function onAuthStateChanged(cb) {
  authListeners.push(cb);
  // Fire immediately with current state
  cb(currentUser);
}

function notifyAuthListeners(user) {
  currentUser = user;
  authListeners.forEach(cb => cb(user));
}

// ── Real Firebase init (lazy) ─────────────────────────────────
let _auth = null;
let _googleProvider = null;
let _signInWithPopup = null;
let _signOut = null;

async function loadFirebase() {
  if (_auth) return true;
  if (!HAS_REAL_CONFIG) return false;
  try {
    const { initializeApp } = await import('https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js');
    const { getAuth, GoogleAuthProvider, signInWithPopup, signOut, onAuthStateChanged: _oasc } =
      await import('https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js');
    const app = initializeApp(FIREBASE_CONFIG);
    _auth = getAuth(app);
    _googleProvider = new GoogleAuthProvider();
    _signInWithPopup = signInWithPopup;
    _signOut = signOut;
    _oasc(_auth, user => {
      notifyAuthListeners(user ? { uid: user.uid, name: user.displayName, email: user.email, photo: user.photoURL } : null);
    });
    return true;
  } catch {
    return false;
  }
}

export async function getAuthToken() {
  if (_auth && _auth.currentUser) {
    return await _auth.currentUser.getIdToken();
  }
  return null;
}

// ── Public actions ─────────────────────────────────────────────
export async function signInWithGoogle() {
  const realFirebase = await loadFirebase();
  if (realFirebase) {
    await _signInWithPopup(_auth, _googleProvider);
  } else {
    // Demo sign-in (no network needed)
    await new Promise(r => setTimeout(r, 800));
    const demoUser = {
      uid: 'demo_' + Math.random().toString(36).slice(2, 8),
      name: 'Demo Analyst',
      email: 'analyst@forensica.ai',
      photo: null,
    };
    notifyAuthListeners(demoUser);
    localStorage.setItem('forensica_demo_user', JSON.stringify(demoUser));
  }
}

export async function signOutUser() {
  if (_signOut && _auth) {
    await _signOut(_auth);
  } else {
    localStorage.removeItem('forensica_demo_user');
    notifyAuthListeners(null);
  }
}

// Restore demo session on page load
(function restoreDemoSession() {
  try {
    const saved = localStorage.getItem('forensica_demo_user');
    if (saved && !HAS_REAL_CONFIG) {
      currentUser = JSON.parse(saved);
    }
  } catch {}
})();

// ── Auth Modal ─────────────────────────────────────────────────
export function initAuth() {
  injectAuthModal();
  injectUserDropdown();

  const googleBtn   = document.getElementById('authGoogleBtn');
  const overlay     = document.getElementById('authModalOverlay');
  const closeBtn    = document.getElementById('authModalClose');
  const userAvatar  = document.getElementById('userAvatar');

  // Close modal on backdrop click or X button
  closeBtn?.addEventListener('click', hideAuthModal);
  overlay?.addEventListener('click', (e) => { if (e.target === overlay) hideAuthModal(); });

  // Google sign-in button inside modal
  googleBtn?.addEventListener('click', async () => {
    googleBtn.disabled = true;
    googleBtn.innerHTML = `<span class="auth-spinner"></span> Signing in…`;
    try {
      await signInWithGoogle();
      hideAuthModal();
    } catch (err) {
      googleBtn.disabled = false;
      googleBtn.innerHTML = googleBtnHTML;
    }
  });

  // Avatar click — open modal if logged out, toggle dropdown if logged in
  userAvatar?.addEventListener('click', (e) => {
    e.stopPropagation();
    if (currentUser) {
      toggleUserDropdown();
    } else {
      showAuthModal();
    }
  });

  // Close dropdown when clicking anywhere outside
  document.addEventListener('click', () => closeUserDropdown());

  // Wire sign-out inside dropdown
  document.addEventListener('click', (e) => {
    if (e.target.id === 'dropdownSignOut' || e.target.closest('#dropdownSignOut')) {
      signOutUser();
      closeUserDropdown();
    }
  });

  // Restore initial UI from demo session / firebase session
  onAuthStateChanged(user => {
    updateAvatarUI(user);
    updateDropdownContent(user);
  });
}

// ── Avatar UI ─────────────────────────────────────────────────
function updateAvatarUI(user) {
  const avatarEl = document.getElementById('userAvatar');
  // Hide old separate sign-out button (replaced by dropdown)
  const oldSignOut = document.getElementById('headerSignOutBtn');
  if (oldSignOut) oldSignOut.style.display = 'none';

  if (!avatarEl) return;

  if (user) {
    const initials = user.name
      ? user.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
      : 'U';
    if (user.photo) {
      avatarEl.innerHTML = `<img src="${user.photo}" alt="${user.name}" style="width:100%;height:100%;border-radius:50%;object-fit:cover">`;
    } else {
      avatarEl.innerHTML = `<span>${initials}</span>`;
    }
    avatarEl.title = 'Account';
    avatarEl.style.cursor = 'pointer';
    avatarEl.style.outline = '2px solid var(--teal)';
  } else {
    avatarEl.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`;
    avatarEl.title = 'Sign in';
    avatarEl.style.cursor = 'pointer';
    avatarEl.style.outline = '';
  }
}

// ── User Dropdown ─────────────────────────────────────────────
function injectUserDropdown() {
  if (document.getElementById('userDropdown')) return;
  const el = document.createElement('div');
  el.id = 'userDropdown';
  el.className = 'user-dropdown hidden';
  el.innerHTML = `
    <div class="ud-user" id="udUserInfo"></div>
    <div class="ud-divider"></div>
    <button class="ud-item" id="dropdownSignOut">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
        <polyline points="16 17 21 12 16 7"/>
        <line x1="21" y1="12" x2="9" y2="12"/>
      </svg>
      Sign out
    </button>
  `;
  // Attach to topnav-right so it positions correctly
  const right = document.querySelector('.topnav-right');
  if (right) right.style.position = 'relative';
  document.getElementById('userAvatar')?.insertAdjacentElement('afterend', el);
}

function updateDropdownContent(user) {
  const info = document.getElementById('udUserInfo');
  if (!info) return;
  if (user) {
    info.innerHTML = `
      <div class="ud-name">${user.name ?? 'Analyst'}</div>
      <div class="ud-email">${user.email ?? ''}</div>
    `;
  }
}

function toggleUserDropdown() {
  const dd = document.getElementById('userDropdown');
  if (!dd) return;
  dd.classList.toggle('hidden');
}

function closeUserDropdown() {
  document.getElementById('userDropdown')?.classList.add('hidden');
}

export function requireAuth(callback) {
  if (currentUser) {
    callback();
  } else {
    showAuthModal(callback);
  }
}

let _pendingCallback = null;

export function showAuthModal(onSuccess = null) {
  _pendingCallback = onSuccess;
  const modal = document.getElementById('authModalOverlay');
  if (modal) modal.classList.remove('hidden');
}

export function hideAuthModal() {
  const modal = document.getElementById('authModalOverlay');
  if (modal) modal.classList.add('hidden');
  if (_pendingCallback && currentUser) {
    const cb = _pendingCallback;
    _pendingCallback = null;
    cb();
  }
  _pendingCallback = null;
}


const googleBtnHTML = `
  <svg width="18" height="18" viewBox="0 0 48 48">
    <path fill="#FFC107" d="M43.611 20.083H42V20H24v8h11.303C33.654 32.657 29.332 36 24 36c-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z"/>
    <path fill="#FF3D00" d="M6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 16.318 4 9.656 8.337 6.306 14.691z"/>
    <path fill="#4CAF50" d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238C29.211 35.091 26.715 36 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z"/>
    <path fill="#1976D2" d="M43.611 20.083H42V20H24v8h11.303a11.987 11.987 0 0 1-4.087 5.571l6.19 5.238C36.971 39.205 44 34 44 24c0-1.341-.138-2.65-.389-3.917z"/>
  </svg>
  Sign in with Google
`;

function injectAuthModal() {
  if (document.getElementById('authModalOverlay')) return;
  const el = document.createElement('div');
  el.id = 'authModalOverlay';
  el.className = 'auth-modal-overlay hidden';
  el.innerHTML = `
    <div class="auth-modal" id="authModal" role="dialog" aria-modal="true" aria-label="Sign in to Forensica AI">
      <button class="auth-modal-close" id="authModalClose" aria-label="Close">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
      <div class="auth-modal-brand">
        <svg width="40" height="40" viewBox="0 0 26 26" fill="none">
          <path d="M13 2L3 7V13C3 18.5 7.5 23.7 13 25C18.5 23.7 23 18.5 23 13V7L13 2Z" fill="url(#amGrad)"/>
          <path d="M9 13L12 16L17 10" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <defs>
            <linearGradient id="amGrad" x1="3" y1="2" x2="23" y2="25">
              <stop offset="0%" stop-color="#0aa89e"/>
              <stop offset="100%" stop-color="#0667d0"/>
            </linearGradient>
          </defs>
        </svg>
        <div>
          <div class="auth-modal-title">Forensica AI</div>
          <div class="auth-modal-sub">Secure Document Verification Platform</div>
        </div>
      </div>
      <p class="auth-modal-msg">Sign in to access your analysis history and saved reports. Your data is protected with Google-grade security.</p>
      <button class="btn-google" id="authGoogleBtn">${googleBtnHTML}</button>
      <p class="auth-modal-note">By signing in, you agree to keep analysis results confidential.</p>
    </div>
  `;
  document.body.appendChild(el);
}
