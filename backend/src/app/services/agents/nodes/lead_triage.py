"""Lead Triage — summarises a CRM lead, scores intent, suggests next actions.

Pure LLM with structured output. Inputs are the lead dict; if only a lead_id
is supplied, we look it up from DuckDB first.
"""

from __future__ import annotations

import logging
from typing import Any

from src.app.services.agents.runtime import emit
from src.app.services.agents.schemas import GraphState, LeadTriageResult
from src.app.services.llm import chat_structured
from src.app.services.duckdb_client import fetch_rows
from src.settings import settings

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a real estate sales coach triaging a CRM lead.

Return strict JSON matching the LeadTriageResult schema:
- summary: 1-2 sentence summary of who this lead is and what they're after.
- intent_score: 1 (cold) to 5 (red-hot). Base it on urgency, budget clarity,
  and how specific the requirements are.
- urgency: low / medium / high.
- suggested_actions: 2-4 concrete next steps the agent should take in the
  next 24-48 hours (e.g. "Send 3 matching listings within budget", "Book a
  20-minute discovery call").
- matched_suburbs: 2-5 NSW suburb names that fit the buyer's brief. Prefer
  suburbs they've named; expand to nearby alternatives.

Australian English. No emojis.
"""


def _lookup_lead(lead_id: str) -> dict[str, Any] | None:
    try:
        cols, rows = fetch_rows("SELECT * FROM leads WHERE lead_id = ? LIMIT 1", [lead_id])
    except Exception as exc:  # noqa: BLE001
        log.warning("lead lookup failed for %s: %s", lead_id, exc)
        return None
    if not rows:
        return None
    return dict(zip(cols, rows[0]))


def _resolve_lead(state: GraphState, inputs: dict[str, Any]) -> dict[str, Any] | None:
    if state.page_context.current_item and "lead_id" in state.page_context.current_item:
        return state.page_context.current_item
    if inputs:
        if isinstance(inputs.get("lead"), dict):
            return inputs["lead"]
        if inputs.get("lead_id"):
            return _lookup_lead(str(inputs["lead_id"]))
    return None


def _fallback_triage(lead: dict[str, Any]) -> LeadTriageResult:
    urgency = str(lead.get("urgency") or "medium").lower()
    if urgency not in {"low", "medium", "high"}:
        urgency = "medium"
    score = {"low": 2, "medium": 3, "high": 4}[urgency]
    suburb = lead.get("preferred_suburb") or "their preferred area"
    return LeadTriageResult(
        summary=(
            f"{lead.get('name', 'Lead')} is {lead.get('intent', 'looking')} in {suburb}. "
            f"Budget ${lead.get('budget_min', 0):,} - ${lead.get('budget_max', 0):,}, "
            f"min {lead.get('min_bed', '?')} bed."
        ),
        intent_score=score,
        urgency=urgency,
        suggested_actions=[
            f"Send 3-5 matching listings in {suburb} within budget",
            "Call within 24 hours to qualify the timeline",
            "Confirm finance pre-approval status",
        ],
        matched_suburbs=[suburb] if isinstance(suburb, str) else [],
    )


async def run(state: GraphState, inputs: dict[str, Any]) -> LeadTriageResult:
    lead = _resolve_lead(state, inputs)
    if lead is None:
        await emit("tool_result", {"node": "lead_triage", "tool": "resolve",
                                    "preview": "no lead found in inputs or page context"})
        return LeadTriageResult(
            summary="No lead supplied — provide a lead_id or open a lead in the Pipeline drawer.",
            intent_score=3,
            urgency="medium",
            suggested_actions=[],
            matched_suburbs=[],
        )

    await emit("tool_call", {"node": "lead_triage", "tool": "summarise", "args": {"lead_id": lead.get("lead_id")}})

    try:
        parsed = chat_structured(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Lead record:\n{lead}"},
            ],
            response_model=LeadTriageResult,
            temperature=0.2,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("lead_triage LLM call failed (%s) — using heuristic", exc)
        parsed = _fallback_triage(lead)

    await emit("tool_result", {
        "node": "lead_triage",
        "tool": "summarise",
        "preview": f"intent {parsed.intent_score}/5, urgency {parsed.urgency}",
    })
    return parsed
