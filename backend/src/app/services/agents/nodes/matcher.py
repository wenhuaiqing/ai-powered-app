"""Property Matcher — Day 1 stub. Day 2 composes data_query + reviews RAG + valuation."""

from __future__ import annotations

from typing import Any

from src.app.services.agents.runtime import emit
from src.app.services.agents.schemas import GraphState, MatcherResult


async def run(state: GraphState, inputs: dict[str, Any]) -> MatcherResult:
    await emit("tool_call", {"node": "matcher", "tool": "compose(data_query+reviews+valuation)", "args": inputs})
    await emit("tool_result", {"node": "matcher", "tool": "compose", "preview": "[stub] 0 candidates"})
    return MatcherResult(
        filter_summary=f"[stub] Property Matcher received: {state.user_message!r}",
        candidates=[],
    )
