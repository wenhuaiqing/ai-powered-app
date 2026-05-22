"""Valuation agent — Day 1 stub. Day 2 wires services/model.py."""

from __future__ import annotations

from typing import Any

from src.app.services.agents.runtime import emit
from src.app.services.agents.schemas import FeatureContribution, GraphState, ValuationResult


async def run(state: GraphState, inputs: dict[str, Any]) -> ValuationResult:
    await emit("tool_call", {"node": "valuation", "tool": "predict_price", "args": inputs or {"placeholder": True}})
    await emit("tool_result", {"node": "valuation", "tool": "predict_price", "preview": "[stub] $0 (Day 2 loads model.pkl)"})
    return ValuationResult(
        predicted_price=0.0,
        confidence_interval=(0.0, 0.0),
        contributions=[FeatureContribution(feature="stub", contribution_aud=0.0)],
        inputs_used=inputs,
    )
