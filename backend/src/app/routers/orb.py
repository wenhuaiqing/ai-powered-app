"""/orb/chat — SSE endpoint that runs the LangGraph and streams typed events."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from src.app.services.agents.graph import build_graph
from src.app.services.agents.runtime import set_queue
from src.app.services.agents.schemas import GraphState, PageContext

log = logging.getLogger(__name__)

router = APIRouter(prefix="/orb", tags=["orb"])

END_TOTAL_TIMEOUT_SECONDS = 90.0


class OrbChatRequest(BaseModel):
    message: str
    page_context: PageContext = Field(default_factory=PageContext)


def _serialise(value: Any) -> str:
    return json.dumps(value, default=_json_default)


def _json_default(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, tuple):
        return list(obj)
    return str(obj)


@router.post("/chat")
async def chat(req: OrbChatRequest) -> EventSourceResponse:
    """Run the orchestrator and stream typed events to the client.

    Event types: planner_decision, node_start, tool_call, tool_result,
    node_end, node_error, final_message, done.
    """
    queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
    set_queue(queue)

    initial = GraphState(user_message=req.message, page_context=req.page_context)
    graph = build_graph()

    async def runner() -> None:
        try:
            await asyncio.wait_for(
                graph.ainvoke(initial),
                timeout=END_TOTAL_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            await queue.put(("node_error", {"name": "graph", "error": "total request timeout"}))
        except Exception as exc:  # noqa: BLE001
            log.exception("graph invocation failed")
            await queue.put(("node_error", {"name": "graph", "error": str(exc)}))
        finally:
            await queue.put(("done", {}))

    task = asyncio.create_task(runner())

    async def event_stream() -> AsyncIterator[dict[str, str]]:
        try:
            while True:
                event_type, data = await queue.get()
                yield {"event": event_type, "data": _serialise(data)}
                if event_type == "done":
                    break
        finally:
            if not task.done():
                task.cancel()

    return EventSourceResponse(event_stream())


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
