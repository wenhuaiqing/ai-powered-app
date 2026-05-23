"""/api/pipeline — CRM leads backed by MySQL (OLTP).

Includes the status state machine + the lead_events audit log. The
Pipeline drawer uses these endpoints to drive lead transitions visibly
on screen.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.app.services.mysql_client import execute, fetch_all, rows_to_dicts

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

LeadStatus = Literal[
    "New", "Contacted", "Qualified", "Viewed",
    "Offered", "Closed Won", "Closed Lost",
]

_LEAD_COLS = """
    le.lead_id, le.name, le.email, le.phone, le.intent, le.status,
    le.min_bed, le.min_bath, le.min_parking, le.preferred_suburb,
    le.max_km_from_cbd, le.budget_min, le.budget_max, le.urgency,
    le.notes, le.created_date, le.assigned_agent_id, a.name AS assigned_agent_name
"""


@router.get("/leads")
async def list_leads(limit: int = Query(50, ge=1, le=200)) -> dict[str, Any]:
    cols, rows = fetch_all(
        f"""
        SELECT {_LEAD_COLS}
        FROM leads le
        LEFT JOIN agents a ON le.assigned_agent_id = a.agent_id
        ORDER BY le.created_date DESC
        LIMIT :lim
        """,
        {"lim": limit},
    )
    items = rows_to_dicts(cols, rows)
    return {"items": items, "count": len(items)}


@router.get("/leads/{lead_id}")
async def get_lead(lead_id: str) -> dict[str, Any]:
    cols, rows = fetch_all(
        f"""
        SELECT {_LEAD_COLS}
        FROM leads le
        LEFT JOIN agents a ON le.assigned_agent_id = a.agent_id
        WHERE le.lead_id = :lid
        """,
        {"lid": lead_id},
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"lead {lead_id} not found")
    return rows_to_dicts(cols, rows)[0]


@router.get("/leads/{lead_id}/events")
async def lead_events(lead_id: str) -> dict[str, Any]:
    cols, rows = fetch_all(
        """
        SELECT event_id, event_type, from_status, to_status, note, actor, created_at
        FROM lead_events
        WHERE lead_id = :lid
        ORDER BY created_at DESC
        LIMIT 50
        """,
        {"lid": lead_id},
    )
    return {"items": rows_to_dicts(cols, rows)}


class StatusUpdate(BaseModel):
    status: LeadStatus
    note: str | None = None
    actor: str = Field(default="user")


@router.post("/leads/{lead_id}/status")
async def update_lead_status(lead_id: str, body: StatusUpdate) -> dict[str, Any]:
    """Transition a lead's status and write an audit row to lead_events.

    Two writes inside one transaction: UPDATE leads, INSERT lead_events.
    """
    current = fetch_all("SELECT status FROM leads WHERE lead_id = :lid", {"lid": lead_id})
    if not current[1]:
        raise HTTPException(status_code=404, detail=f"lead {lead_id} not found")
    from_status = current[1][0][0]
    if from_status == body.status:
        return {"lead_id": lead_id, "status": body.status, "changed": False}

    from src.app.services.mysql_client import get_engine
    with get_engine().begin() as conn:
        from sqlalchemy import text
        conn.execute(
            text("UPDATE leads SET status = :status WHERE lead_id = :lid"),
            {"status": body.status, "lid": lead_id},
        )
        conn.execute(
            text("""
                INSERT INTO lead_events (lead_id, event_type, from_status, to_status, note, actor)
                VALUES (:lid, 'status_change', :from_status, :to_status, :note, :actor)
            """),
            {
                "lid": lead_id,
                "from_status": from_status,
                "to_status": body.status,
                "note": body.note,
                "actor": body.actor,
            },
        )
    return {"lead_id": lead_id, "status": body.status, "changed": True, "from": from_status}


@router.get("/_stats/overview")
async def overview_stats() -> dict[str, Any]:
    cols, rows = fetch_all(
        """
        SELECT
            COUNT(*)                                                  AS total,
            SUM(CASE WHEN urgency = 'high'    THEN 1 ELSE 0 END)      AS hot,
            SUM(CASE WHEN intent = 'Buying'   THEN 1 ELSE 0 END)      AS buyers,
            SUM(CASE WHEN intent = 'Renting'  THEN 1 ELSE 0 END)      AS renters,
            AVG(budget_max)                                           AS avg_budget_max
        FROM leads
        """
    )
    return rows_to_dicts(cols, rows)[0]
