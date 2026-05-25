"""Compliance RAG agent — local-corpus retrieval over NSW regulations + Tavily fallback.

Workflow:
  1. Embed the query and pull the top-k chunks from regulations/embeddings.parquet.
  2. If max score < FALLBACK_THRESHOLD, also run a domain-restricted Tavily search.
  3. Feed both sets of citations into the LLM with `response_format=ComplianceResult`
     so the answer + confidence + cited sources all come back typed.

Degrades gracefully when keys are missing — returns the retrieval-only answer
or a clearly-labelled placeholder.
"""

from __future__ import annotations

import logging
from typing import Any

from src.app.services.agents.runtime import emit
from src.app.services.agents.schemas import (
    Citation,
    ComplianceResult,
    GraphState,
)
from src.app.services.llm import chat_structured
from src.app.services.rag.regulations import retrieve
from src.app.services.tools.web_search import web_search
from src.settings import settings

log = logging.getLogger(__name__)

FALLBACK_THRESHOLD = 0.55
NSW_DOMAINS = ["legislation.nsw.gov.au", "fairtrading.nsw.gov.au", "revenue.nsw.gov.au", "firb.gov.au"]

SYSTEM_PROMPT = """\
You are a NSW property-regulation analyst answering questions for real estate
agents and buyers/tenants. Use ONLY the provided citations to answer. Every
fact must be tied to a citation by including the source name inline, e.g.
"(Fair Trading NSW)".

Rules:
- Australian English. No emojis.
- If the citations do not cover the question, set confidence to "low" and
  say so honestly. Do not invent numbers, dates, or section references.
- Quote AUD figures with dollar signs ($35,029).
- Keep the answer tight: 3-6 short sentences, or a short bullet list when
  numbers/conditions clearly benefit.
- Set `used_web_fallback` to true if any citation has source_type == "web".

Return strict JSON matching the ComplianceResult schema.
"""


def _resolve_query(state: GraphState, inputs: dict[str, Any]) -> str:
    explicit = (inputs or {}).get("query")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    return state.user_message


async def _fallback_from_citations(citations: list[Citation]) -> str:
    """When no LLM is available, return a concatenated answer from the citations."""
    if not citations:
        return ("I couldn't find a NSW-regulation match for that question. "
                "Try rephrasing, or check the source links if any were returned.")
    head = citations[0]
    body = head.snippet
    if len(citations) > 1:
        body += f"\n\nAlso relevant: {citations[1].snippet[:400]}"
    return body


async def run(state: GraphState, inputs: dict[str, Any]) -> ComplianceResult:
    query = _resolve_query(state, inputs)
    await emit("tool_call", {"node": "compliance", "tool": "regulations_retrieve", "args": {"query": query, "k": 4}})
    local_hits = retrieve(query, k=4)
    max_score = max((c.score for c in local_hits), default=0.0)
    await emit("tool_result", {
        "node": "compliance",
        "tool": "regulations_retrieve",
        "preview": f"{len(local_hits)} hit(s), top score {max_score:.2f}"
                   + (f", top source: {local_hits[0].source}" if local_hits else ""),
    })

    used_fallback = False
    if max_score < FALLBACK_THRESHOLD:
        await emit("tool_call", {"node": "compliance", "tool": "web_search",
                                  "args": {"query": query, "domains": NSW_DOMAINS, "k": 4}})
        web_hits = await web_search(query, k=4, include_domains=NSW_DOMAINS, search_depth="advanced")
        await emit("tool_result", {
            "node": "compliance",
            "tool": "web_search",
            "preview": f"{len(web_hits)} web hit(s) (fallback triggered, max local score {max_score:.2f})",
        })
        for hit in web_hits:
            local_hits.append(Citation(
                source=hit.title or hit.url,
                url=hit.url,
                snippet=hit.snippet[:600],
                score=hit.score,
                source_type="web",
            ))
            used_fallback = True

    # Build the LLM prompt and ask for a strict ComplianceResult
    citation_block = "\n\n".join(
        f"[{i+1}] source={c.source} | url={c.url or ''} | source_type={c.source_type}\n{c.snippet}"
        for i, c in enumerate(local_hits)
    ) or "(no citations retrieved)"

    user_payload = (
        f"Question: {query}\n\n"
        f"Available citations:\n{citation_block}"
    )

    try:
        parsed = chat_structured(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_payload},
            ],
            response_model=ComplianceResult,
            temperature=0.1,
        )
        # Ensure we don't lose the actual retrieved citations if the LLM omits them
        if not parsed.citations:
            parsed.citations = local_hits
        parsed.used_web_fallback = parsed.used_web_fallback or used_fallback
        return parsed
    except Exception as exc:  # noqa: BLE001
        log.warning("compliance LLM call failed (%s) — falling back to retrieval-only answer", exc)
        answer = await _fallback_from_citations(local_hits)
        confidence = "low" if max_score < FALLBACK_THRESHOLD else "medium"
        return ComplianceResult(
            answer=answer,
            citations=local_hits,
            confidence=confidence,
            used_web_fallback=used_fallback,
        )
