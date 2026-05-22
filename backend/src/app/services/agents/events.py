"""Helpers for typed SSE events streamed from /orb/chat."""

from __future__ import annotations

import json
from typing import Any, Literal

EventType = Literal[
    "planner_decision",
    "node_start",
    "tool_call",
    "tool_result",
    "node_end",
    "node_error",
    "final_message",
    "done",
]


def sse(event: EventType, data: dict[str, Any]) -> dict[str, str]:
    """Format an event in the shape expected by sse-starlette EventSourceResponse."""
    return {"event": event, "data": json.dumps(data, default=_json_default)}


def _json_default(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, tuple):
        return list(obj)
    return str(obj)
