"""/api/dashboard — KPI rollups + recent agent activity feed.

KPIs come from the DuckDB analytics tables (denormalised by the ETL).
Recent runs come from MySQL (OLTP) — written as each orb call finishes.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Query

from src.app.services.duckdb_client import fetch_rows
from src.app.services.mysql_client import fetch_all, rows_to_dicts

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/kpis")
async def kpis() -> dict[str, Any]:
    cols, rows = fetch_rows(
        """
        SELECT
            (SELECT COUNT(*) FROM listings)                       AS total_listings,
            (SELECT COUNT(*) FROM listings WHERE status='For Sale')  AS for_sale,
            (SELECT COUNT(*) FROM listings WHERE status='For Lease') AS for_lease,
            (SELECT COUNT(*) FROM listings WHERE stage='Under Offer')AS under_offer,
            (SELECT COUNT(*) FROM leads)                          AS leads,
            (SELECT COUNT(*) FROM leads WHERE urgency='high')     AS hot_leads,
            (SELECT AVG(days_on_market)::INT FROM listings)       AS avg_days_on_market,
            (SELECT COUNT(DISTINCT suburb) FROM properties)       AS suburbs_covered,
            (SELECT MEDIAN(price)::INT FROM properties)           AS median_sale_price
        """
    )
    return dict(zip(cols, rows[0]))


@router.get("/recent-runs")
async def recent_runs(limit: int = Query(15, ge=1, le=50)) -> dict[str, Any]:
    """Latest orb invocations. Powers the Dashboard activity feed."""
    cols, rows = fetch_all(
        """
        SELECT
            run_id, user_message, page_module, agents_called,
            used_web_search, error_count, duration_ms,
            related_lead_id, related_listing_id, created_at
        FROM agent_runs
        ORDER BY created_at DESC
        LIMIT :lim
        """,
        {"lim": limit},
    )
    items = rows_to_dicts(cols, rows)
    for item in items:
        raw = item.get("agents_called")
        if isinstance(raw, str):
            try:
                item["agents_called"] = json.loads(raw)
            except json.JSONDecodeError:
                item["agents_called"] = []
        item["used_web_search"] = bool(item.get("used_web_search"))
        # created_at is already normalised to an ISO+Z string by
        # mysql_client._coerce.
    return {"items": items, "count": len(items)}
