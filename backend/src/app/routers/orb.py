"""/orb/chat — SSE endpoint that runs the LangGraph and streams typed events.

/orb/run-agent — same plumbing but bypasses the planner. Used by cross-module
buttons ("Estimate value", "Draft listing", "Triage lead") that already know
which agent they want and pass the row's context in directly.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, field_validator
from sse_starlette.sse import EventSourceResponse

from src.app.services.agents.graph import build_graph
from src.app.services.auth import has_write_token
from src.app.services.rate_limit import enforce_orb_rate_limit
from src.app.services.agents.runs import from_event_log
from src.app.services.agents.runtime import set_queue
from src.app.services.agents.schemas import (
    AgentCall,
    AgentName,
    GraphState,
    PageContext,
    PlannerDecision,
)
from src.settings import settings

log = logging.getLogger(__name__)

router = APIRouter(prefix="/orb", tags=["orb"])

# Both orb routes are rate limited (per-IP + global) - see services/rate_limit.py.
_limited = [Depends(enforce_orb_rate_limit)]

END_TOTAL_TIMEOUT_SECONDS = 90.0


class OrbChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=settings.orb_max_message_chars)
    page_context: PageContext = Field(default_factory=PageContext)


class OrbRunAgentRequest(BaseModel):
    agent: AgentName
    inputs: dict[str, Any] = Field(default_factory=dict)
    # Optional user message for context in the summariser.
    message: str = Field(default="", max_length=settings.orb_max_message_chars)
    page_context: PageContext = Field(default_factory=PageContext)

    @field_validator("inputs")
    @classmethod
    def _bound_inputs(cls, value: dict[str, Any]) -> dict[str, Any]:
        serialised = json.dumps(value, default=str)
        if len(serialised) > settings.orb_max_context_chars:
            raise ValueError(f"inputs too large (max {settings.orb_max_context_chars} chars)")
        return value


def _serialise(value: Any) -> str:
    return json.dumps(value, default=_json_default)


def _json_default(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, tuple):
        return list(obj)
    return str(obj)


async def _run_graph_sse(initial: GraphState, *, trusted: bool = False) -> EventSourceResponse:
    """Common SSE plumbing — runs the graph, drains a queue, streams events,
    then persists the run to MySQL (agent_runs) for the activity feed.

    `trusted` marks runs made with the demo write token; only those have
    their prompt shown verbatim on the public Dashboard feed."""
    queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
    set_queue(queue)
    graph = build_graph()
    started_at = time.monotonic()

    async def runner() -> None:
        try:
            await asyncio.wait_for(graph.ainvoke(initial), timeout=END_TOTAL_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            await queue.put(("node_error", {"name": "graph", "error": "total request timeout"}))
        except Exception:  # noqa: BLE001
            # Detail stays in the server log; clients get a generic message.
            log.exception("graph invocation failed")
            await queue.put(("node_error", {"name": "graph", "error": "internal error while running the agents"}))
        finally:
            await queue.put(("done", {}))

    task = asyncio.create_task(runner())

    async def event_stream() -> AsyncIterator[dict[str, str]]:
        events: list[tuple[str, dict[str, Any]]] = []
        try:
            while True:
                event_type, data = await queue.get()
                events.append((event_type, data))
                yield {"event": event_type, "data": _serialise(data)}
                if event_type == "done":
                    break
        finally:
            if not task.done():
                task.cancel()
            try:
                duration_ms = int((time.monotonic() - started_at) * 1000)
                ctx_dump = initial.page_context.model_dump() if initial.page_context else {}
                from_event_log(
                    user_message=initial.user_message or "",
                    page_module=ctx_dump.get("module"),
                    page_context=ctx_dump,
                    events=events,
                    duration_ms=duration_ms,
                    trusted=trusted,
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("agent_runs persistence skipped: %s", exc)

    return EventSourceResponse(event_stream())


@router.post("/chat", dependencies=_limited)
async def chat(req: OrbChatRequest, request: Request) -> EventSourceResponse:
    """Run the orchestrator and stream typed events to the client.

    Event types: planner_decision, node_start, tool_call, tool_result,
    node_end, node_error, final_message, done.
    """
    initial = GraphState(user_message=req.message, page_context=req.page_context)
    return await _run_graph_sse(initial, trusted=has_write_token(request))


@router.post("/run-agent", dependencies=_limited)
async def run_agent(req: OrbRunAgentRequest, request: Request) -> EventSourceResponse:
    """Invoke a specific agent directly. Skips the planner LLM call.

    Used by cross-module buttons that already know which agent they want —
    "Estimate value" / "Draft listing" / "Compliance check" on a Properties
    row, "Triage lead" / "Match properties" on a Pipeline row, etc.
    """
    pre_planned = PlannerDecision(
        agents_to_call=[AgentCall(
            name=req.agent,
            inputs_json=json.dumps(req.inputs, default=str),
            reasoning=f"Direct invocation from {req.page_context.module}.",
        )],
        reasoning=f"Cross-module call: {req.agent} on {req.page_context.module}.",
        needs_clarification=False,
    )
    user_message = req.message or _default_message(req.agent, req.page_context)
    initial = GraphState(
        user_message=user_message,
        page_context=req.page_context,
        planner_decision=pre_planned,
    )
    return await _run_graph_sse(initial, trusted=has_write_token(request))


def _default_message(agent: AgentName, ctx: PageContext) -> str:
    """Fallback user_message used to ground the summariser when the caller
    doesn't provide one. Specific enough that the summariser knows what to
    explain in the final answer."""
    label = (ctx.current_item or {}).get("address") or (ctx.current_item or {}).get("name") or ctx.module
    return {
        "valuation":    f"Estimate the value of the selected property ({label}).",
        "listing":      f"Draft listing copy for the selected property ({label}).",
        "compliance":   f"Run a compliance check for the selected item ({label}).",
        "lead_triage":  f"Triage the selected lead ({label}).",
        "matcher":      f"Match properties for the selected lead ({label}).",
        "market_watch": f"Pull current market news relevant to {label}.",
        "data_query":   f"Summarise the data relevant to {label}.",
    }.get(agent, f"Run the {agent} agent.")


@router.get("/agents")
async def list_agents() -> dict[str, list[dict[str, str]]]:
    """Reference list of the agents exposed by the orb."""
    return {
        "agents": [
            {"name": "compliance",   "label": "Compliance",      "summary": "NSW Fair Trading, Residential Tenancies, stamp duty, FIRB, strata."},
            {"name": "data_query",   "label": "Data Query",      "summary": "Text-to-DuckDB over properties/suburbs/listings/leads."},
            {"name": "matcher",      "label": "Property Matcher","summary": "Composes data + suburb reviews + valuation to rank candidates."},
            {"name": "valuation",    "label": "Valuation",       "summary": "RandomForest price prediction with feature contributions."},
            {"name": "listing",      "label": "Listing Drafter", "summary": "Generates listing copy from property attributes."},
            {"name": "lead_triage",  "label": "Lead Triage",     "summary": "Summarises a CRM lead, scores intent, suggests actions."},
            {"name": "market_watch", "label": "Market Watch",    "summary": "Live web search via Tavily for property-market news."},
        ]
    }
