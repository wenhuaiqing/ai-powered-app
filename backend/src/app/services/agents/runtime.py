"""Shared runtime helpers for streaming events out of LangGraph nodes.

LangGraph nodes only receive `state` — they don't get the SSE queue. We use a
ContextVar so any node can call `emit(event, data)` and the queue, set up by
the /orb/chat endpoint per-request, picks it up.
"""

from __future__ import annotations

import asyncio
from contextvars import ContextVar
from typing import Any

_events_queue: ContextVar[asyncio.Queue[tuple[str, dict[str, Any]]]] = ContextVar(
    "_events_queue"
)


def set_queue(queue: asyncio.Queue[tuple[str, dict[str, Any]]]) -> None:
    _events_queue.set(queue)


async def emit(event: str, data: dict[str, Any]) -> None:
    """Push a typed event for the SSE endpoint to forward.

    Silently no-ops when no queue is set (e.g. when running a node from a
    unit test without the SSE wrapper).
    """
    try:
        queue = _events_queue.get()
    except LookupError:
        return
    await queue.put((event, data))
