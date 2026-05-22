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
    return out
