# Multi-stage build for the FastAPI backend.
#
# Stage 1 (builder): uv-managed dependency resolution into a .venv.
# Stage 2 (runtime): copies the venv + source into a slim Python image,
# runs uvicorn. No build tooling in the runtime layer.
#
# data/ (model.pkl + the embedding parquets + regulation source docs) IS
# baked into the image -- Fargate filesystems are ephemeral per-task, and
# rebuilding the parquets + retraining the model on every container boot
# would be too expensive + needs Azure-embed access. The only data
# artefact we DON'T ship is platform.duckdb; the startup ETL rebuilds
# that from MySQL on every boot (see CMD below).

# ---------- builder ----------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Cache the dependency layer separately from the source. uv sync without
# the project itself installs only the locked deps.
COPY backend/pyproject.toml backend/uv.lock ./backend/
RUN --mount=type=cache,target=/root/.cache/uv \
    cd backend && uv sync --frozen --no-install-project --no-dev

# Now copy the source and finalise the install.
COPY backend/src ./backend/src
COPY backend/tests ./backend/tests
RUN --mount=type=cache,target=/root/.cache/uv \
    cd backend && uv sync --frozen --no-dev

# Scripts + misc go in too -- the seed task image and the app image share
# the same Dockerfile output (different CMDs).
COPY scripts ./scripts
COPY misc ./misc

# Pre-built data artefacts (excluding platform.duckdb via .dockerignore).
# Model, embeddings, regulation docs all ship in the image.
COPY data ./data


# ---------- runtime ----------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/backend/.venv/bin:$PATH"

# Run as non-root.
RUN groupadd --system app && useradd --system --gid app --home /app app

WORKDIR /app
COPY --from=builder --chown=app:app /app /app

# /app is created by WORKDIR as root before USER switches to app, so even
# though the COPY chowns the contents, the parent dir stays root-owned
# and the app user can't create new subdirs in it. Fix + pre-create the
# data dir so the startup ETL can write the DuckDB.
RUN chown app:app /app && \
    mkdir -p /app/data && chown app:app /app/data

USER app
EXPOSE 8000

# Default CMD: rebuild DuckDB from MySQL on every boot (Fargate gives each
# task its own ephemeral filesystem, so the seeded DuckDB from a sibling
# task is not visible here). ETL is ~3s. Then exec uvicorn so it becomes
# PID 1 and receives signals correctly.
# Override via task-def `command` for the seed task (which skips the ETL).
WORKDIR /app/backend
CMD ["sh", "-c", "python ../scripts/etl_mysql_to_duckdb.py && exec uvicorn src.main:app --host 0.0.0.0 --port 8000"]
