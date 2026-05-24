# Multi-stage build for the FastAPI backend.
#
# Stage 1 (builder): uv-managed dependency resolution into a .venv.
# Stage 2 (runtime): copies the venv + source into a slim Python image,
# runs uvicorn. No build tooling in the runtime layer.
#
# data/ (model.pkl, duckdb, parquet) is NOT baked in here -- it's either
# mounted as a volume locally (docker-compose) or seeded via the ECS
# `seed_all.py` task against RDS + a regenerated DuckDB on a shared
# volume in AWS. Keeping data/ out of the image makes builds fast +
# provider-agnostic (Azure vs Bedrock embeddings have different dims).

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


# ---------- runtime ----------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/backend/.venv/bin:$PATH"

# Run as non-root.
RUN groupadd --system app && useradd --system --gid app --home /app app

WORKDIR /app
COPY --from=builder --chown=app:app /app /app

USER app
EXPOSE 8000

# Default CMD runs the FastAPI app. Override to e.g.
# ["python", "scripts/seed_all.py"] for the ECS seed task.
WORKDIR /app/backend
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
