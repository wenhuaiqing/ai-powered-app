"""FastAPI application entry."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.routers import orb
from src.settings import settings

app = FastAPI(
    title="ai-powered-app",
    description="Reapit One-Platform demo — multi-agent orchestration over Sydney house-price data.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(orb.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
