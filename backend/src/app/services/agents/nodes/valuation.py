"""Valuation agent — wraps services/model.py.

Inputs typically come from the planner, which extracts bed/bath/size/suburb
etc. from the user's prompt. The Properties drawer button also passes the
property dict in `state.page_context.current_item`. Missing fields are
enriched with suburb medians + dataset baselines inside services/model.py.
"""

from __future__ import annotations

import logging
from typing import Any

from src.app.services.agents.runtime import emit
from src.app.services.agents.schemas import GraphState, ValuationResult
from src.app.services.model import predict_with_contributions

log = logging.getLogger(__name__)

ACCEPTED_KEYS = {
    "num_bed", "num_bath", "num_parking", "property_size",
    "suburb", "km_from_cbd", "type",
    "suburb_population", "suburb_median_income", "suburb_sqkm",
    "suburb_lat", "suburb_lng", "suburb_elevation",
    "cash_rate", "property_inflation_index",
}


def _merge_inputs(state: GraphState, planner_inputs: dict[str, Any]) -> dict[str, Any]:
    """Page-context property fields (lowest priority) overridden by planner-extracted fields."""
    merged: dict[str, Any] = {}
    if state.page_context.current_item:
        for key, val in state.page_context.current_item.items():
            if key in ACCEPTED_KEYS and val not in (None, ""):
                merged[key] = val
    for key, val in (planner_inputs or {}).items():
        if key in ACCEPTED_KEYS and val not in (None, ""):
            merged[key] = val
    return merged


async def run(state: GraphState, inputs: dict[str, Any]) -> ValuationResult:
    features = _merge_inputs(state, inputs)
    await emit("tool_call", {"node": "valuation", "tool": "predict_price", "args": features})
    try:
        result = predict_with_contributions(features)
    except RuntimeError as exc:
        # Model not trained yet — return a clear placeholder rather than crashing.
        log.warning("Valuation skipped: %s", exc)
        result = ValuationResult(
            predicted_price=0.0,
            confidence_interval=(0.0, 0.0),
            contributions=[],
            inputs_used=features,
        )
        await emit("tool_result", {"node": "valuation", "tool": "predict_price",
                                    "preview": f"model not available: {exc}"})
        return result

    await emit("tool_result", {
        "node": "valuation",
        "tool": "predict_price",
        "preview": (
            f"${result.predicted_price:,.0f} "
            f"(80% CI ${result.confidence_interval[0]:,.0f}-${result.confidence_interval[1]:,.0f})"
        ),
    })
    return result
