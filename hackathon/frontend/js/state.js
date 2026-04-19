/**
 * state.js — Application state store
 *
 * Single source of truth for all UI state.
 * Modules import and mutate this store via exported setters.
 */

export const appState = {
  currentPage: 'home',
  sidebarOpen: true,

  // Document lifecycle
  document: null,     // { id, filename, size_bytes, pages, uploaded_at }
  uploadStatus: 'idle', // idle | uploading | uploaded | error

  // Analysis job
  job: null,          // { job_id, document_id, status }
  analysisStatus: 'idle', // idle | running | complete | error

  // Results payload (from GET /analysis/{id})
  results: null,

  // Report payload (from GET /report/{id})
  report: null,

  // Viewer settings
  viewer: {
    zoom: 100,
    showBoundingBoxes: true,
    showHeatmap: false,
    focusedAnomalyId: null,
  },
};

/** Merge partial updates into appState */
export function setState(partial) {
  Object.assign(appState, partial);
}

export function setViewerState(partial) {
  Object.assign(appState.viewer, partial);
}
