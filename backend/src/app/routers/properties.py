"""/api/properties — listings backed by MySQL (OLTP).

Joins listings -> properties -> suburbs -> agents in SQL so the API
response shape matches the legacy DuckDB `listings_enriched` view.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query

from src.app.services.mysql_client import fetch_all, rows_to_dicts

router = APIRouter(prefix="/api/properties", tags=["properties"])

StatusFilter = Literal["all", "For Sale", "For Lease"]


_BASE_SELECT = """
    SELECT
        l.listing_id,
        l.status,
        l.stage,
        l.asking_price,
        l.listed_date,
        l.days_on_market,
        a.name AS agent_name,
        p.suburb,
        p.num_bed,
        p.num_bath,
        p.num_parking,
        p.property_size,
        p.property_type AS type,
        p.km_from_cbd,
        s.region,
        s.median_house_price_2021,
        s.family_friendliness,
        s.safety,
        p.suburb_lat,
        p.suburb_lng,
        p.property_id,
        l.headline,
        l.body_markdown
    FROM listings l
    JOIN properties p ON l.property_id = p.property_id
    LEFT JOIN agents a ON l.agent_id = a.agent_id
    LEFT JOIN suburbs s ON LOWER(s.name) = LOWER(p.suburb)
"""


@router.get("/list")
async def list_properties(
    status: StatusFilter = "all",
    limit: int = Query(60, ge=1, le=200),
) -> dict[str, Any]:
    where = ""
    params: dict[str, Any] = {"lim": limit}
    if status != "all":
        where = "WHERE l.status = :status"
        params["status"] = status
    cols, rows = fetch_all(
        f"{_BASE_SELECT} {where} ORDER BY l.listed_date DESC LIMIT :lim",
        params,
    )
    items = rows_to_dicts(cols, rows)
    return {"items": items, "count": len(items)}


@router.get("/{listing_id}")
async def get_property(listing_id: str) -> dict[str, Any]:
    cols, rows = fetch_all(
        f"{_BASE_SELECT} WHERE l.listing_id = :lid",
        {"lid": listing_id},
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"listing {listing_id} not found")
    return rows_to_dicts(cols, rows)[0]


@router.get("/_stats/overview")
async def overview_stats() -> dict[str, Any]:
    cols, rows = fetch_all(
        """
        SELECT
            SUM(CASE WHEN status = 'For Sale'    THEN 1 ELSE 0 END) AS for_sale,
            SUM(CASE WHEN status = 'For Lease'   THEN 1 ELSE 0 END) AS for_lease,
            SUM(CASE WHEN stage  = 'Under Offer' THEN 1 ELSE 0 END) AS under_offer,
            AVG(days_on_market)                                     AS avg_days_on_market,
            COUNT(DISTINCT p.suburb)                                AS suburbs
        FROM listings l
        JOIN properties p ON l.property_id = p.property_id
        """
    )
    return rows_to_dicts(cols, rows)[0]
