# Multi-stage build for the React/Vite frontend.
#
# Stage 1 (builder): node 20 builds the Vite bundle.
# Stage 2 (runtime): nginx serves dist/ with an SPA fallback and proxies
# /api, /orb, /health to the backend. Same origin -> no CORS round-trip
# + the bundle stays URL-agnostic.

# ---------- builder ----------
FROM node:20-alpine AS builder

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# ---------- runtime ----------
FROM nginx:1.27-alpine AS runtime

COPY --from=builder /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# nginx:alpine listens on 80 by default; expose for clarity.
EXPOSE 80

# nginx -g 'daemon off;' is the image's default CMD; no override needed.
