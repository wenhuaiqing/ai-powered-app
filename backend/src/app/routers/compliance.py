"""/api/compliance — direct RAG search for the Compliance Hub page."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from src.app.services.rag.regulations import retrieve

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


@router.get("/search")
async def search(q: str = Query(..., min_length=2), k: int = Query(5, ge=1, le=10)) -> dict[str, Any]:
    citations = retrieve(q, k=k)
    return {
        "query": q,
        "count": len(citations),
        "citations": [c.model_dump() for c in citations],
    }
