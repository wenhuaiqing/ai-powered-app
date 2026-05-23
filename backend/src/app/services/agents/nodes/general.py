"""General chat agent — the catch-all fallback for anything outside the
7 specialist niches.

Routes here for:
  - "How does this app work?" / "What can you do?"
  - Casual greetings + onboarding
  - General real-estate chat with no clear specialist fit
  - Questions about the platform itself

Always returns a typed GeneralResult so the UI renders it the same way as
the other agents (answer card with confidence + suggested_followups). The
suggested follow-ups surface specialist agents the user might want to
escalate to, which gently teaches the platform's capabilities.
"""

from __future__ import annotations

import logging
from typing import Any

from src.app.services.agents.runtime import emit
from src.app.services.agents.schemas import GeneralResult, GraphState
from src.app.services.ai_client import chat_model, get_openai_client
from src.settings import settings

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are Rai, the AppMarket co-pilot for Reapit — a mock "One Platform"
demo built around Sydney house-price data. Your job is to be a useful,
friendly assistant for anything that doesn't cleanly fit one of the
specialist agents.

The platform has 7 specialist agents you can refer the user to:
  - Compliance:       NSW property regulations (stamp duty, FIRB,
                      tenancy, strata, etc.) with cited sources.
  - Data Query:       Natural-language analytics over our DuckDB
                      tables (properties, suburbs, listings, leads).
  - Property Matcher: Ranks suburbs for a buyer/tenant brief.
  - Valuation:        RandomForest price prediction (trained on 11k
                      NSW sales, 2016-2022).
  - Listing Drafter:  Writes property listing copy.
  - Lead Triage:      Scores a CRM lead, suggests next actions.
  - Market Watch:     Live property-market news via web search.

Six modules in the sidebar: Dashboard, Properties, Pipeline, Valuations,
Compliance Hub, Market Insights.

Rules:
- Australian English. No emojis.
- Tight answers — 2-4 sentences, occasionally a short list.
- If the user's question would be better answered by a specialist
  agent, surface 1-3 concrete follow-up prompts they could send next
  (e.g. "What stamp duty applies to a $900k purchase in NSW?"). Put
  these in `suggested_followups`.
- If you don't know, say so honestly and set confidence = "low".
- Never invent factual numbers (prices, regulation thresholds, dates).
  Defer to the specialist agents for those.

Return strict JSON matching the GeneralResult schema.
"""


def _fallback(question: str) -> GeneralResult:
    return GeneralResult(
        answer=(
            "I'm Rai, the AppMarket co-pilot for this Reapit demo. I can route your "
            "question to specialist agents — try asking about NSW stamp duty, suburb "
            "matching, or a property valuation."
        ),
        confidence="low",
        suggested_followups=[
            "What stamp duty applies to a $900k purchase in NSW?",
            "Find me family-friendly 3-bed suburbs under $1.5M within 20km of CBD",
            "Estimate the value of a 4-bed house in Manly with 800sqm",
        ],
    )


async def run(state: GraphState, inputs: dict[str, Any]) -> GeneralResult:
    question = (inputs or {}).get("question") or state.user_message

    if not settings.azure_openai_api_key:
        result = _fallback(question)
        await emit("tool_result", {"node": "general", "tool": "chat",
                                    "preview": "(no LLM) returning onboarding suggestions"})
        return result

    await emit("tool_call", {"node": "general", "tool": "chat", "args": {"prompt": question}})

    try:
        client = get_openai_client()
        completion = client.beta.chat.completions.parse(
            model=chat_model(),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"User message: {question}\n\nPage: {state.page_context.module}"},
            ],
            response_format=GeneralResult,
            temperature=0.3,
        )
        result = completion.choices[0].message.parsed
        if result is None:
            raise ValueError("general agent returned no parsed payload")
    except Exception as exc:  # noqa: BLE001
        log.warning("general agent LLM call failed (%s) — using fallback text", exc)
        result = _fallback(question)

    preview_bits = [f"confidence {result.confidence}"]
    if result.suggested_followups:
        preview_bits.append(f"{len(result.suggested_followups)} follow-up{'' if len(result.suggested_followups)==1 else 's'}")
    await emit("tool_result", {"node": "general", "tool": "chat", "preview": " · ".join(preview_bits)})
    return result
