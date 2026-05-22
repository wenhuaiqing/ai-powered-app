// Vite proxy forwards /orb, /dashboard, etc. to http://localhost:8000 in dev,
// so an empty base means "same origin". Override via VITE_API_BASE_URL for
// the deployed (Phase 2) build.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
