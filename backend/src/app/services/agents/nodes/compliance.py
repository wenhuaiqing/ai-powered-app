"""Compliance RAG agent — Day 1 stub.

Day 2 will wire `services/rag/regulations.py` + Tavily fallback. For now this
returns a placeholder result so the SSE stream is end-to-end testable.
"""

from __future__ import annotations

from typing import Any

from src.app.services.agents.runtime import emit
from src.app.services.agents.schemas import ComplianceResult, GraphState


async def run(state: GraphState, inputs: dict[str, Any]) -> ComplianceResult:
    await emit("tool_call", {"node": "compliance", "tool": "regulations_retrieve", "args": {"query": state.user_message, "k": 4}})
    await emit("tool_result", {"node": "compliance", "tool": "regulations_retrieve", "preview": "[stub] 0 chunks (Day 2 wires the RAG corpus)"})
    return ComplianceResult(
        answer=f"[stub] Compliance agent received: {state.user_message!r}. Day 2 will return cited NSW regulatory text.",
        citations=[],
        confidence="low",
        used_web_fallback=False,
    )
