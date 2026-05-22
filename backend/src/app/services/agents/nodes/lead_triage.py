"""Lead Triage — Day 1 stub. Day 2 makes a real LLM call with structured output."""

from __future__ import annotations

from typing import Any

from src.app.services.agents.schemas import GraphState, LeadTriageResult


async def run(state: GraphState, inputs: dict[str, Any]) -> LeadTriageResult:
    return LeadTriageResult(
        summary=f"[stub] Lead Triage received: inputs={inputs!r}",
        intent_score=3,
        urgency="medium",
        suggested_actions=["[stub] Day 2 will return real next-action suggestions."],
        matched_suburbs=[],
    )
