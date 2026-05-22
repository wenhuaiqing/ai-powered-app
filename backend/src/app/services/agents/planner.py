"""Planner — LLM router that decides which specialist agents to invoke.

Uses OpenAI structured outputs to enforce the PlannerDecision schema. Falls
back to a keyword heuristic when no API key is configured (lets the SSE
endpoint stay testable without credentials).
"""

from __future__ import annotations

import logging
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
the following specialist agents to call to answer the user's question. You may
call zero, one, or several agents. Return strict JSON.

Available agents:
- compliance: NSW property/tenancy/stamp-duty/FIRB/strata regulation Q&A (RAG
  over a curated corpus + web fallback). Use for any legal/regulatory question.
- data_query: Natural-language questions answered by SQL over our DuckDB
  tables (properties, suburbs, listings, leads). Use for analytics, stats,
  filtering, counts.
- matcher: Buyer/tenant requirement matching. Filters properties, looks up
  suburb reviews, runs valuations to rank candidates.
- valuation: Predict a price for a specific property described in the prompt
  (bed/bath/size/suburb/km-from-cbd, etc.).
- listing: Draft listing copy from a property's attributes.
- lead_triage: Summarise a CRM lead, score intent (1-5), suggest next steps.
- market_watch: Live web search for current property-market news, recent
  regulatory changes, or competitor listings (uses Tavily).

Return JSON matching this schema:
{
  "agents_to_call": [
    {"name": "<agent>", "inputs": {...}, "reasoning": "..."}
  ],
  "reasoning": "<one sentence on the overall plan>",
  "needs_clarification": false
}

Pick the smallest set of agents that gets the job done. If the question is
casual chit-chat with no clear intent, return an empty agents_to_call list.
"""


_KEYWORD_RULES: list[tuple[tuple[str, ...], AgentName]] = [
    (("stamp duty", "tenanc", "bond", "fair trading", "firb", "strata", "underquot", "disclosure"), "compliance"),
    (("market", "this week", "news", "trend", "recent", "right now", "current"), "market_watch"),
    (("draft listing", "write listing", "listing copy", "listing description"), "listing"),
    (("triage", "intent score", "next action", "lead summary"), "lead_triage"),
    (("match", "find me", "looking for", "buyer", "tenant", "suburbs under"), "matcher"),
    (("estimate", "valuation", "value of", "worth", "predict price", "predicted"), "valuation"),
    (("how many", "average", "median", "count", "top", "compare", "list"), "data_query"),
]


def _heuristic_decision(message: str) -> PlannerDecision:
    lower = message.lower()
    chosen: list[AgentName] = []
    for keywords, agent in _KEYWORD_RULES:
        if any(kw in lower for kw in keywords) and agent not in chosen:
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
