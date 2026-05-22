"""/api/dashboard — KPI rollups for the home page."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.app.services.duckdb_client import fetch_rows

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
