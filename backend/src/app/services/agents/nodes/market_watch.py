"""Market Watch agent — live web search via Tavily.

Answers questions the static datasets can't:
  - "What's happening in the Sydney property market this week?"
  - "Any recent NSW stamp duty changes?"
  - "Find competitor listings on Domain.com.au for a 3-bed in Manly."

Returns a MarketWatchResult with cited URLs. The LLM step (synthesise an
answer from the hits) is best-effort — if Azure OpenAI is unavailable, we
return the top snippets verbatim as the answer.
"""

from __future__ import annotations

import logging
from typing import Any

from src.app.services.agents.runtime import emit
from src.app.services.agents.schemas import GraphState, MarketWatchResult
from src.app.services.ai_client import chat_model, get_openai_client
from src.app.services.tools.web_search import web_search
from src.settings import settings

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a property-market analyst. Synthesise a tight 3-6 sentence answer to
the user's question using ONLY the supplied web search hits. Cite source
publication names inline, like "(ABC News)". If the hits don't cover the
question, say so honestly. Australian English. No emojis.
"""


def _resolve_query(state: GraphState, inputs: dict[str, Any]) -> str:
    explicit = (inputs or {}).get("query")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    return state.user_message


async def _synthesise(question: str, hits: list[dict[str, Any]]) -> str:
    if not hits:
        return ("I couldn't find any relevant web results for that question. "
                "Try a more specific query or check the Insights tab for our local data.")
    if not settings.azure_openai_api_key:
        # Minimal "no LLM" fallback: stitch the top two snippets together.
        head = hits[0]
        out = f"{head['snippet']} ({head['title']})"
        if len(hits) > 1:
            out += f"\n\nAlso: {hits[1]['snippet']} ({hits[1]['title']})"
        return out
    try:
        client = get_openai_client()
        payload = "\n\n".join(
            f"[{i+1}] {h['title']} — {h['url']}\n{h['snippet']}"
            for i, h in enumerate(hits)
        )
        completion = client.chat.completions.create(
            model=chat_model(),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Question: {question}\n\nHits:\n{payload}"},
            ],
            temperature=0.2,
        )
        return completion.choices[0].message.content or "(no synthesised answer)"
    except Exception as exc:  # noqa: BLE001
        log.warning("market_watch synthesis failed (%s) — returning top snippet", exc)
        head = hits[0]
        return f"{head['snippet']} ({head['title']})"


async def run(state: GraphState, inputs: dict[str, Any]) -> MarketWatchResult:
    query = _resolve_query(state, inputs)
    await emit("tool_call", {"node": "market_watch", "tool": "web_search", "args": {"query": query, "k": 5}})

    hits = await web_search(query=query, k=5, search_depth="advanced")
    hit_dicts = [h.model_dump() for h in hits]

    await emit("tool_result", {
        "node": "market_watch",
        "tool": "web_search",
        "preview": f"{len(hits)} hit(s)" + (f" — top: {hits[0].title}" if hits else " (none)"),
    })

    answer = await _synthesise(query, hit_dicts)
    return MarketWatchResult(answer=answer, hits=hits, query_used=query)
