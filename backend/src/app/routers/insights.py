"""/api/insights — aggregations for the Market Insights dashboards."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.app.services.duckdb_client import fetch_rows

router = APIRouter(prefix="/api/insights", tags=["insights"])


def _rows_to_dicts(cols: list[str], rows: list[list[Any]]) -> list[dict[str, Any]]:
    return [dict(zip(cols, r)) for r in rows]


@router.get("/price-distribution")
async def price_distribution() -> dict[str, Any]:
    cols, rows = fetch_rows(
        """
        WITH bins AS (
            SELECT
                CAST(price / 100000 AS INT) * 100000 AS price_bucket,
                COUNT(*) AS n
            FROM properties
            WHERE price BETWEEN 100000 AND 5000000
            GROUP BY 1
        )
        SELECT price_bucket, n FROM bins ORDER BY price_bucket LIMIT 100
        """
    )
    return {"bins": _rows_to_dicts(cols, rows)}


@router.get("/price-vs-distance")
async def price_vs_distance() -> dict[str, Any]:
    cols, rows = fetch_rows(
        """
        SELECT ROUND(km_from_cbd, 0) AS km_from_cbd,
               AVG(price)::INT       AS avg_price,
               COUNT(*)              AS n
        FROM properties
        WHERE km_from_cbd IS NOT NULL AND price BETWEEN 100000 AND 5000000
        GROUP BY 1
        ORDER BY 1 LIMIT 100
        """
    )
    return {"points": _rows_to_dicts(cols, rows)}


@router.get("/beds-breakdown")
async def beds_breakdown() -> dict[str, Any]:
    cols, rows = fetch_rows(
        """
        SELECT num_bed, COUNT(*) AS n, AVG(price)::INT AS avg_price, MEDIAN(price)::INT AS median_price
        FROM properties
        WHERE num_bed BETWEEN 1 AND 6
        GROUP BY num_bed ORDER BY num_bed LIMIT 10
        """
    )
    return {"breakdown": _rows_to_dicts(cols, rows)}


@router.get("/top-suburbs")
async def top_suburbs(limit: int = 12) -> dict[str, Any]:
    cols, rows = fetch_rows(
        """
        SELECT suburb,
               COUNT(*)              AS sales,
               MEDIAN(price)::INT    AS median_price,
               AVG(km_from_cbd)::INT AS avg_km_from_cbd
        FROM properties
        WHERE price IS NOT NULL
        GROUP BY suburb
        HAVING COUNT(*) >= 5
        ORDER BY median_price DESC LIMIT ?
        """,
        [limit],
    )
    return {"suburbs": _rows_to_dicts(cols, rows)}


@router.get("/suburb-medians")
async def suburb_medians(limit: int = 200) -> dict[str, Any]:
    cols, rows = fetch_rows(
        """
        SELECT suburb,
               ANY_VALUE(suburb_lat) AS lat,
               ANY_VALUE(suburb_lng) AS lng,
               MEDIAN(price)::INT    AS median_price,
               COUNT(*)              AS n
        FROM properties
        WHERE suburb_lat IS NOT NULL AND suburb_lng IS NOT NULL
        GROUP BY suburb
        HAVING COUNT(*) >= 3
        ORDER BY n DESC LIMIT ?
        """,
        [limit],
    )
    return {"suburbs": _rows_to_dicts(cols, rows)}
