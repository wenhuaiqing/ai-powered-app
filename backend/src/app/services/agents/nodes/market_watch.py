"""Market Watch — Day 1 stub. Day 2 wires Tavily."""

from __future__ import annotations

from typing import Any

from src.app.services.agents.runtime import emit
from src.app.services.agents.schemas import GraphState, MarketWatchResult


async def run(state: GraphState, inputs: dict[str, Any]) -> MarketWatchResult:
    await emit("tool_call", {"node": "market_watch", "tool": "web_search", "args": {"query": state.user_message}})
    await emit("tool_result", {"node": "market_watch", "tool": "web_search", "preview": "[stub] 0 hits (Day 2 wires Tavily)"})
    return MarketWatchResult(
        answer=f"[stub] Market Watch received: {state.user_message!r}. Day 2 will return live news with cited URLs.",
        hits=[],
        query_used=state.user_message,
    )
