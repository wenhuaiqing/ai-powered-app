"""Persist each orb run to MySQL after the graph finishes.

The orb SSE loop wraps a real LangGraph invocation in a queue drain; we
record one row per run so the Dashboard "Recent agent activity" feed has
real data and so we can replay prompts against new model versions later.

Writes are best-effort — a MySQL outage must not break the orb response.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.app.services.mysql_client import execute

log = logging.getLogger(__name__)


def record_run(
    *,
    user_message: str,
    page_module: str | None,
    agents_called: list[str],
    final_message: str | None,
    used_web_search: bool,
    error_count: int,
    duration_ms: int,
    related_lead_id: str | None = None,
    related_listing_id: str | None = None,
) -> int | None:
    """Insert one agent_runs row. Returns the row id, or None on failure."""
    try:
        return execute(
            """
            INSERT INTO agent_runs (
                user_message, page_module, agents_called, final_message,
                used_web_search, error_count, duration_ms,
                related_lead_id, related_listing_id
            ) VALUES (
                :user_message, :page_module, :agents_called, :final_message,
                :used_web_search, :error_count, :duration_ms,
                :related_lead_id, :related_listing_id
            )
            """,
            {
                "user_message":      user_message[:2000] if user_message else "",
                "page_module":       page_module,
                "agents_called":     json.dumps(agents_called),
                "final_message":     final_message,
                "used_web_search":   1 if used_web_search else 0,
                "error_count":       int(error_count),
                "duration_ms":       int(duration_ms),
                "related_lead_id":   related_lead_id,
                "related_listing_id": related_listing_id,
            },
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to persist agent_run: %s", exc)
        return None


def _related_ids_from_context(page_ctx: dict[str, Any] | None) -> tuple[str | None, str | None]:
    if not page_ctx:
        return None, None
    item = page_ctx.get("current_item") or {}
    if not isinstance(item, dict):
        return None, None
    return item.get("lead_id"), item.get("listing_id")


def from_event_log(
    *,
    user_message: str,
    page_module: str | None,
    page_context: dict[str, Any] | None,
    events: list[tuple[str, dict[str, Any]]],
    duration_ms: int,
) -> int | None:
    """Helper: derive the summary fields from the queue's event log."""
    agents_called: list[str] = []
    used_web_search = False
    error_count = 0
    final_message: str | None = None

    for evt_type, data in events:
        if evt_type == "node_start":
            name = data.get("name")
            if name and name not in agents_called and name not in ("planner", "summariser"):
                agents_called.append(name)
        elif evt_type == "tool_call":
            tool = data.get("tool")
            if tool and "web_search" in tool:
                used_web_search = True
        elif evt_type == "node_error":
            error_count += 1
        elif evt_type == "final_message":
            final_message = data.get("message") or data.get("final_message")

    lead_id, listing_id = _related_ids_from_context(page_context)
    return record_run(
        user_message=user_message,
        page_module=page_module,
        agents_called=agents_called,
        final_message=final_message,
        used_web_search=used_web_search,
        error_count=error_count,
        duration_ms=duration_ms,
        related_lead_id=lead_id,
        related_listing_id=listing_id,
    )
