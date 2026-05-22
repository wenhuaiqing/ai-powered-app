"""Planner — LLM router that decides which specialist agents to invoke.

Uses OpenAI structured outputs to enforce the PlannerDecision schema. Falls
back to a keyword heuristic when no API key is configured (lets the SSE
endpoint stay testable without credentials).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from src.app.services.ai_client import chat_model, get_openai_client
from src.app.services.agents.schemas import (
    AgentCall,
    AgentName,
    GraphState,
    PlannerDecision,
)
from src.settings import settings

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the planner for a multi-agent real-estate assistant. Decide which of
the following specialist agents to call. You may call zero, one, or several
agents. Return strict JSON.

For each call, `inputs_json` is a JSON-encoded STRING (not an object) holding
the keyword arguments the agent expects. Use the exact key names below.

Agents and their inputs:
- compliance: NSW regulation Q&A (RAG + web fallback).
    inputs_json: {"query": "<the user's question>"}
- data_query: Natural-language analytics over DuckDB tables (properties,
  suburbs, listings, leads).
    inputs_json: {"question": "<the user's question>"}
- matcher: Buyer/tenant requirement matching. Use flat keys.
    inputs_json: {"min_bed": <int>, "max_price": <number aud>,
                  "max_km_from_cbd": <number>, "lifestyle": "<short text>",
                  "preferred_suburb": "<optional suburb name>"}
- valuation: Predict a price for a described property. Use flat keys.
    inputs_json: {"num_bed": <int>, "num_bath": <int>, "num_parking": <int>,
                  "property_size": <sqm>, "suburb": "<name>", "type": "House|Apartment|..."}
- listing: Draft listing copy from a property's attributes.
    inputs_json: <same keys as valuation>
- lead_triage: Summarise + score a CRM lead.
    inputs_json: {"lead_id": "<id>"} or {"lead": {...full lead dict...}}
- market_watch: Live web search.
    inputs_json: {"query": "<focused search query>"}

Rules:
- Return strict JSON matching the PlannerDecision schema.
- `inputs_json` MUST be a JSON-encoded STRING. Example value:
  "{\\"min_bed\\": 3, \\"max_price\\": 1500000}"
- If a field is unknown, omit it. Never invent a suburb or price.
- Pick the smallest set of agents that gets the job done.
- If the user is just chatting (no clear intent), return an empty
  agents_to_call list.
"""


# Keyword rules use word-boundary regex to avoid false positives
# (e.g. "Bondi" must not match the "bond" compliance keyword).
_KEYWORD_RULES: list[tuple[tuple[str, ...], AgentName]] = [
    (("stamp duty", "tenancy", "tenant rights", "rental bond", "bonds", "fair trading",
      "firb", "strata", "underquoting", "disclosure", "cooling off",
      "regulation", "compliance", "legal"), "compliance"),
    (("market this week", "this week", "news", "trend", "trends", "recently",
      "recent changes", "right now", "current", "live market"), "market_watch"),
    (("draft listing", "write listing", "listing copy", "listing description"), "listing"),
    (("triage", "intent score", "next action", "lead summary", "triage this lead"), "lead_triage"),
    (("match", "find me", "looking for", "buyer", "renter", "tenant",
      "suburbs under", "ranked suburbs"), "matcher"),
    (("estimate", "valuation", "value of", "what's it worth", "worth",
      "predict price", "predicted price"), "valuation"),
    (("how many", "average", "median", "count", "top", "compare",
      "list", "show me", "breakdown"), "data_query"),
]


def _matches(keyword: str, text: str) -> bool:
    """Match a keyword as a whole word/phrase (case-insensitive)."""
    pattern = r"\b" + re.escape(keyword) + r"\b"
    return re.search(pattern, text, re.IGNORECASE) is not None


def _heuristic_decision(message: str) -> PlannerDecision:
    chosen: list[AgentName] = []
    for keywords, agent in _KEYWORD_RULES:
        if any(_matches(kw, message) for kw in keywords) and agent not in chosen:
            chosen.append(agent)
    if not chosen:
        chosen = ["data_query"]  # safe default: try to answer from local data
    return PlannerDecision(
        agents_to_call=[AgentCall(name=name, reasoning="heuristic match") for name in chosen],
        reasoning="No LLM available; routed by keyword heuristic.",
        needs_clarification=False,
    )


async def plan(state: GraphState) -> PlannerDecision:
    if not settings.azure_openai_api_key:
        return _heuristic_decision(state.user_message)

    page_ctx = state.page_context.model_dump()
    user_payload = (
        f"User message: {state.user_message}\n"
        f"Page context: {page_ctx}"
    )
    try:
        client = get_openai_client()
        completion = client.beta.chat.completions.parse(
            model=chat_model(),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_payload},
            ],
            response_format=PlannerDecision,
            temperature=0,
        )
        decision = completion.choices[0].message.parsed
        if decision is None:
            raise ValueError("planner returned no parsed payload")
        return decision
    except Exception as exc:  # noqa: BLE001
        log.warning("Planner LLM call failed (%s) — falling back to heuristic", exc)
        return _heuristic_decision(state.user_message)
