"""/api/valuations — direct ML predict + model-info for the Valuations module.

Used by the Predictor form (no agent overhead) and the Model Explorer tab.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.app.services.model import predict_with_contributions
from src.settings import settings

router = APIRouter(prefix="/api/valuations", tags=["valuations"])


class PredictRequest(BaseModel):
    num_bed: int = Field(ge=0, le=15)
    num_bath: int = Field(ge=0, le=15)
    num_parking: int = Field(ge=0, le=10)
    property_size: float = Field(gt=0, le=20_000)
    suburb: str
    type: str = "House"


@router.post("/predict")
async def predict(req: PredictRequest) -> dict[str, Any]:
    try:
        result = predict_with_contributions(req.model_dump())
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return result.model_dump()


@router.get("/suburbs")
async def list_suburbs() -> dict[str, Any]:
    """All distinct suburbs from `properties`, sorted alphabetically.

    Used by the Valuations Predictor form to populate a searchable dropdown
    so users can't typo a suburb (which would silently fall through to the
    model's "Other" bucket via enrich_features).
    """
    from src.app.services.duckdb_client import fetch_rows
    cols, rows = fetch_rows(
        """
        SELECT suburb, COUNT(*) AS sales
        FROM properties
        WHERE suburb IS NOT NULL
        GROUP BY suburb
        ORDER BY suburb
        """
    )
    return {"suburbs": [{"name": r[0], "sales": r[1]} for r in rows]}


@router.get("/model-info")
async def model_info() -> dict[str, Any]:
    data_dir = Path(settings.data_dir)
    out: dict[str, Any] = {}
    for key, filename in [
        ("metrics", "metrics.json"),
        ("feature_importance", "feature_importance.json"),
        ("residuals", "residuals.json"),
    ]:
        path = data_dir / filename
        if path.exists():
            out[key] = json.loads(path.read_text(encoding="utf-8"))
        else:
            out[key] = None

    # Date range of the training data — surfaced in the Valuations UI so
    # users know the model is anchored to 2016-2022 NSW sales, not today's
    # prices.
    from src.app.services.duckdb_client import fetch_rows
    _, rows = fetch_rows(
        """
        SELECT MIN(date_sold)::DATE, MAX(date_sold)::DATE, COUNT(date_sold)
        FROM properties
        WHERE date_sold IS NOT NULL
        """
    )
    if rows:
        r = rows[0]
        out["data_range"] = {
            "earliest": str(r[0]) if r[0] else None,
            "latest":   str(r[1]) if r[1] else None,
            "earliest_year": r[0].year if r[0] else None,
            "latest_year":   r[1].year if r[1] else None,
            "n_with_date":   r[2],
        }
    return out
