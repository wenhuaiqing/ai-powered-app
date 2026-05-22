"""Summariser — composes a final user-facing reply from the agents' results."""

from __future__ import annotations

import logging

from src.app.services.ai_client import chat_model, get_openai_client
from src.app.services.agents.schemas import AgentName, FinalMessage, GraphState
from src.settings import settings

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the summariser for a real-estate AI assistant. Given the user's
question and the structured outputs from one or more specialist agents,
compose a clear, concise reply for the user.

Rules:
- Australian English. No emojis.
- Quote AUD figures with dollar signs, e.g. $850,000.
- When citations are present (Compliance / Market Watch), include them inline
  as plain-text footnote-style references (e.g. "(Fair Trading NSW)") and list
  the URLs at the end.
- Keep replies tight — usually 3-6 short sentences. Use bullet points only
  when the data clearly benefits from them.
- If the agents returned errors or partial data, say so honestly.
"""


def _used_agents(state: GraphState) -> list[AgentName]:
    used: list[AgentName] = []
    if state.compliance_result is not None:
        used.append("compliance")
    if state.data_query_result is not None:
        used.append("data_query")
    if state.valuation_result is not None:
        used.append("valuation")
    if state.matcher_result is not None:
        used.append("matcher")
    if state.listing_draft is not None:
        used.append("listing")
    if state.lead_triage_result is not None:
        used.append("lead_triage")
    if state.market_watch_result is not None:
        used.append("market_watch")
    return used


def _fallback_summary(state: GraphState, agents: list[AgentName]) -> str:
    if not agents and not state.errors:
        return (
            "I couldn't find anything to action for that question. Try asking "
            "about a suburb, a price estimate, a regulation, or current market news."
        )
    parts = []
    if state.compliance_result:
        parts.append(state.compliance_result.answer)
    if state.market_watch_result:
        parts.append(state.market_watch_result.answer)
    if state.valuation_result:
        v = state.valuation_result
        lo, hi = v.confidence_interval
        parts.append(f"Predicted price: ${v.predicted_price:,.0f} (range ${lo:,.0f}-${hi:,.0f}).")
    if state.matcher_result:
        parts.append(state.matcher_result.filter_summary)
    if state.data_query_result and state.data_query_result.interpretation:
        parts.append(state.data_query_result.interpretation)
    if state.listing_draft:
        parts.append(state.listing_draft.headline)
    if state.lead_triage_result:
        parts.append(state.lead_triage_result.summary)
    if state.errors:
        err_msgs = ", ".join(f"{e.node}: {e.message}" for e in state.errors)
        parts.append(f"(Some agents had errors: {err_msgs})")
    return "\n\n".join(parts) if parts else "No agent produced a result."


async def summarise(state: GraphState) -> FinalMessage:
    used = _used_agents(state)

    if not settings.azure_openai_api_key:
        return FinalMessage(message=_fallback_summary(state, used), used_agents=used)

    payload = {
        "user_message": state.user_message,
        "compliance": state.compliance_result.model_dump() if state.compliance_result else None,
        "data_query": state.data_query_result.model_dump() if state.data_query_result else None,
        "valuation": state.valuation_result.model_dump() if state.valuation_result else None,
        "matcher": state.matcher_result.model_dump() if state.matcher_result else None,
        "listing": state.listing_draft.model_dump() if state.listing_draft else None,
        "lead_triage": state.lead_triage_result.model_dump() if state.lead_triage_result else None,
        "market_watch": state.market_watch_result.model_dump() if state.market_watch_result else None,
        "errors": [e.model_dump() for e in state.errors],
    }

    try:
        client = get_openai_client()
        completion = client.chat.completions.create(
            model=chat_model(),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": str(payload)},
            ],
            temperature=0.2,
        )
        text = completion.choices[0].message.content or _fallback_summary(state, used)
    except Exception as exc:  # noqa: BLE001
        log.warning("Summariser LLM call failed (%s) — using fallback text", exc)
        text = _fallback_summary(state, used)

    return FinalMessage(message=text, used_agents=used)
