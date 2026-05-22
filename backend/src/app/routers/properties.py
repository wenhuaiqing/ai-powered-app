"""/api/properties — list + detail views over the listings_enriched DuckDB view."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query

from src.app.services.duckdb_client import fetch_rows

router = APIRouter(prefix="/api/properties", tags=["properties"])

StatusFilter = Literal["all", "For Sale", "For Lease"]


def _rows_to_dicts(cols: list[str], rows: list[list[Any]]) -> list[dict[str, Any]]:
    return [dict(zip(cols, r)) for r in rows]


@router.get("/list")
async def list_properties(
    status: StatusFilter = "all",
    limit: int = Query(60, ge=1, le=200),
) -> dict[str, Any]:
    where_clauses = []
    params: list[Any] = []
    if status != "all":
        where_clauses.append("status = ?")
        params.append(status)
    where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    params.append(limit)
    cols, rows = fetch_rows(
        f"""
        SELECT listing_id, status, stage, asking_price, listed_date, days_on_market,
               agent_name, suburb, num_bed, num_bath, num_parking, property_size,
               type, km_from_cbd, region, median_house_price_2021, family_friendliness,
               safety, suburb_lat, suburb_lng, property_id
        FROM listings_enriched
        {where}
        ORDER BY listed_date DESC
        LIMIT ?
        """,
        params,
    )
    items = _rows_to_dicts(cols, rows)
    return {"items": items, "count": len(items)}


@router.get("/{listing_id}")
async def get_property(listing_id: str) -> dict[str, Any]:
    cols, rows = fetch_rows("SELECT * FROM listings_enriched WHERE listing_id = ?", [listing_id])
    if not rows:
        raise HTTPException(status_code=404, detail=f"listing {listing_id} not found")
    return _rows_to_dicts(cols, rows)[0]


@router.get("/_stats/overview")
async def overview_stats() -> dict[str, Any]:
    cols, rows = fetch_rows(
        """
        SELECT
            COUNT(*) FILTER (WHERE status = 'For Sale')   AS for_sale,
            COUNT(*) FILTER (WHERE status = 'For Lease')  AS for_lease,
            COUNT(*) FILTER (WHERE stage = 'Under Offer') AS under_offer,
            AVG(days_on_market)                            AS avg_days_on_market,
            COUNT(DISTINCT suburb)                         AS suburbs
        FROM listings_enriched
        """
    )
    return _rows_to_dicts(cols, rows)[0]
