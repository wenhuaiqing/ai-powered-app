import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    // Only proxy the backend-only paths. /properties, /pipeline, etc. are
    // SPA routes the frontend owns — Vite must serve index.html for them.
    // Backend routers for those modules will live under /api/* in Day 4.
    proxy: {
      "/orb":    { target: "http://localhost:8000", changeOrigin: true },
      "/api":    { target: "http://localhost:8000", changeOrigin: true },
      "/health": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
