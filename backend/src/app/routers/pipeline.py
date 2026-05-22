"""/api/pipeline — synthetic CRM leads list + detail."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from src.app.services.duckdb_client import fetch_rows

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


def _rows_to_dicts(cols: list[str], rows: list[list[Any]]) -> list[dict[str, Any]]:
    return [dict(zip(cols, r)) for r in rows]


@router.get("/leads")
async def list_leads(limit: int = Query(50, ge=1, le=200)) -> dict[str, Any]:
    cols, rows = fetch_rows(
        """
        SELECT lead_id, name, email, phone, intent, min_bed, min_bath, min_parking,
               preferred_suburb, max_km_from_cbd, budget_min, budget_max, urgency,
               notes, created_date
        FROM leads
        ORDER BY created_date DESC
        LIMIT ?
        """,
        [limit],
    )
    items = _rows_to_dicts(cols, rows)
    return {"items": items, "count": len(items)}


@router.get("/leads/{lead_id}")
async def get_lead(lead_id: str) -> dict[str, Any]:
    cols, rows = fetch_rows("SELECT * FROM leads WHERE lead_id = ?", [lead_id])
    if not rows:
        raise HTTPException(status_code=404, detail=f"lead {lead_id} not found")
    return _rows_to_dicts(cols, rows)[0]


@router.get("/_stats/overview")
async def overview_stats() -> dict[str, Any]:
    cols, rows = fetch_rows(
        """
        SELECT
            COUNT(*)                                  AS total,
            COUNT(*) FILTER (WHERE urgency = 'high')  AS hot,
            COUNT(*) FILTER (WHERE intent = 'Buying') AS buyers,
            COUNT(*) FILTER (WHERE intent = 'Renting')AS renters,
            AVG(budget_max)                           AS avg_budget_max
        FROM leads
        """
    )
    return _rows_to_dicts(cols, rows)[0]
