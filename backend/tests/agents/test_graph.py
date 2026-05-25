"""End-to-end graph test — runs the compiled LangGraph with a real query.

Without API keys this exercises the heuristic-fallback paths in every node.
"""

from __future__ import annotations

import asyncio

import pytest

from src.app.services.agents.graph import build_graph
from src.app.services.agents.runtime import set_queue
from src.app.services.agents.schemas import GraphState


@pytest.mark.asyncio
async def test_graph_runs_and_streams_events():
    queue: asyncio.Queue = asyncio.Queue()
    set_queue(queue)
    graph = build_graph()

    initial = GraphState(user_message="What stamp duty applies to a $900k purchase?")

    async def runner():
        try:
            await graph.ainvoke(initial)
        finally:
            await queue.put(("done", {}))

    task = asyncio.create_task(runner())
    events: list[str] = []
    while True:
        ev, _ = await queue.get()
        events.append(ev)
        if ev == "done":
            break
    await task

    # We must always see the planner decision, at least one node_start, a
    # final_message, and the done marker.
    assert "planner_decision" in events
    assert events.count("node_start") >= 2
    assert "final_message" in events
    assert events[-1] == "done"


@pytest.mark.asyncio
async def test_graph_invalid_sql_is_caught(monkeypatch):
    """A bogus draft SQL should be rejected by the validator and the run still completes."""
    from src.app.services.agents.nodes import data_query as dq

    class _BadDraft:
        sql = "DROP TABLE properties"
        interpretation = "evil"

    async def fake_ask(*a, **kw):  # noqa: ANN001
        return _BadDraft()

    monkeypatch.setattr(dq, "_ask_llm", fake_ask)
    # LLM path is always live now (Bedrock); _ask_llm is mocked above.

    queue: asyncio.Queue = asyncio.Queue()
    set_queue(queue)

    state = GraphState(user_message="how many properties do we have?")
    result = await dq.run(state, {})
    assert result.validation_passed is False
    assert any("forbidden" in e.lower() or "allowlist" in e.lower() for e in result.validation_errors)
