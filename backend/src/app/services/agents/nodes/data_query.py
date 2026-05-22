"""Data Query agent (text-to-DuckDB) — Day 1 stub."""

from __future__ import annotations

from typing import Any

from src.app.services.agents.runtime import emit
from src.app.services.agents.schemas import DataQueryResult, GraphState


async def run(state: GraphState, inputs: dict[str, Any]) -> DataQueryResult:
    placeholder_sql = "SELECT 1 AS placeholder LIMIT 1"
    await emit("tool_call", {"node": "data_query", "tool": "duckdb_query", "args": {"sql": placeholder_sql}})
    await emit("tool_result", {"node": "data_query", "tool": "duckdb_query", "preview": "[stub] 1 row returned"})
    return DataQueryResult(
        sql=placeholder_sql,
        columns=["placeholder"],
        rows=[[1]],
        row_count=1,
        interpretation=f"[stub] Data Query agent received: {state.user_message!r}. Day 2 will generate real DuckDB SQL.",
        validation_passed=True,
    )
