"""LangGraph topology — Planner -> agents_runner -> Summariser.

Day 1 keeps the agents in a single sequential `agents_runner` node iterating
the planner's chosen list. Day 2 can promote each agent to its own LangGraph
node + parallel `Send` edges, but the contract (typed state, SSE events) stays
the same.
"""

from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from typing import Any, Awaitable, Callable

from langgraph.graph import END, START, StateGraph

from src.app.services.agents.nodes import (
    compliance,
    data_query,
    lead_triage,
    listing,
    market_watch,
    matcher,
    valuation,
)
from src.app.services.agents.planner import plan
from src.app.services.agents.runtime import emit
from src.app.services.agents.schemas import (
    AgentName,
    GraphState,
    NodeError,
)
from src.app.services.agents.summariser import summarise

log = logging.getLogger(__name__)

PER_NODE_TIMEOUT_SECONDS = 30.0

NODE_RUNNERS: dict[AgentName, Callable[[GraphState, dict[str, Any]], Awaitable[Any]]] = {
    "compliance": compliance.run,
    "data_query": data_query.run,
    "matcher": matcher.run,
    "valuation": valuation.run,
    "listing": listing.run,
    "lead_triage": lead_triage.run,
    "market_watch": market_watch.run,
}

# Map an agent name to the GraphState field that holds its result.
RESULT_FIELDS: dict[AgentName, str] = {
    "compliance": "compliance_result",
    "data_query": "data_query_result",
    "matcher": "matcher_result",
    "valuation": "valuation_result",
    "listing": "listing_draft",
    "lead_triage": "lead_triage_result",
    "market_watch": "market_watch_result",
}


async def _planner_node(state: GraphState) -> dict[str, Any]:
    # /orb/run-agent pre-populates planner_decision to invoke a specific
    # agent directly. In that case we skip the LLM call but still emit the
    # same event sequence so the frontend trace renders identically.
    if state.planner_decision is not None:
        await emit("node_start", {"name": "planner"})
        await emit("planner_decision", state.planner_decision.model_dump())
        await emit("node_end", {"name": "planner", "result": state.planner_decision.model_dump()})
        return {}

    await emit("node_start", {"name": "planner"})
    try:
        decision = await asyncio.wait_for(plan(state), timeout=PER_NODE_TIMEOUT_SECONDS)
    except Exception as exc:  # noqa: BLE001
        log.exception("planner node failed")
        await emit("node_error", {"name": "planner", "error": str(exc)})
        return {"errors": state.errors + [NodeError(node="planner", message=str(exc))]}

    await emit("planner_decision", decision.model_dump())
    await emit("node_end", {"name": "planner", "result": decision.model_dump()})
    return {"planner_decision": decision}


async def _agents_runner_node(state: GraphState) -> dict[str, Any]:
    if state.planner_decision is None:
        return {}

    updates: dict[str, Any] = {}
    errors = list(state.errors)
    for call in state.planner_decision.agents_to_call:
        if call.name not in NODE_RUNNERS:
            await emit("node_error", {"name": call.name, "error": "unknown agent"})
            errors.append(NodeError(node=call.name, message="unknown agent"))
            continue

        await emit("node_start", {"name": call.name, "inputs": call.inputs})
        try:
            result = await asyncio.wait_for(
                NODE_RUNNERS[call.name](state, call.inputs),
                timeout=PER_NODE_TIMEOUT_SECONDS,
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("agent node %s failed", call.name)
            await emit("node_error", {"name": call.name, "error": str(exc)})
            errors.append(NodeError(node=call.name, message=str(exc)))
            continue

        field = RESULT_FIELDS[call.name]
        updates[field] = result
        await emit("node_end", {"name": call.name, "result": result.model_dump()})

    updates["errors"] = errors
    return updates


async def _summariser_node(state: GraphState) -> dict[str, Any]:
    await emit("node_start", {"name": "summariser"})
    try:
        final = await asyncio.wait_for(summarise(state), timeout=PER_NODE_TIMEOUT_SECONDS)
    except Exception as exc:  # noqa: BLE001
        log.exception("summariser failed")
        await emit("node_error", {"name": "summariser", "error": str(exc)})
        message = "Sorry, I ran into a problem composing the final answer."
        await emit("final_message", {"message": message, "used_agents": []})
        return {
            "final_message": message,
            "errors": state.errors + [NodeError(node="summariser", message=str(exc))],
        }

    await emit("final_message", final.model_dump())
    await emit("node_end", {"name": "summariser", "result": final.model_dump()})
    return {"final_message": final.message}


@lru_cache(maxsize=1)
def build_graph():
    """Compile the LangGraph once per process."""
    g = StateGraph(GraphState)
    g.add_node("planner", _planner_node)
    g.add_node("agents_runner", _agents_runner_node)
    g.add_node("summariser", _summariser_node)
    g.add_edge(START, "planner")
    g.add_edge("planner", "agents_runner")
    g.add_edge("agents_runner", "summariser")
    g.add_edge("summariser", END)
    return g.compile()
