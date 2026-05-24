"""Data Query agent — text-to-DuckDB with validator + interpreter.

Flow:
 1. LLM emits {sql, interpretation} via structured output.
 2. sql_validator.validate() asserts SELECT-only, allowlisted tables,
    LIMIT injected.
 3. If invalid, one retry with the validation errors embedded in the
    follow-up prompt.
 4. duckdb_client executes the validated SQL.
 5. Returns DataQueryResult with sql, rows, columns, interpretation,
    validation flags.

Schema is introspected from DuckDB so changes to the data layer surface
automatically in the LLM prompt — no PAGE_SCHEMAS to keep in sync.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

from src.app.services.agents.runtime import emit
from src.app.services.agents.schemas import DataQueryResult, GraphState
from src.app.services.llm import chat_structured
from src.app.services.duckdb_client import describe_table, fetch_rows
from src.app.services.sql_validator import ALLOWED_TABLES, validate
from src.settings import settings

log = logging.getLogger(__name__)

MAX_RETRIES = 1


class _Draft(BaseModel):
    sql: str = Field(description="DuckDB SELECT/WITH query. Only the tables in the allowlist.")
    interpretation: str = Field(description="One-sentence explanation of what the query does.")


SYSTEM_PROMPT_TEMPLATE = """\
You generate DuckDB SQL to answer the user's question against the read-only
schema below. Return strict JSON: {{"sql": "...", "interpretation": "..."}}.

Schema:
{schema}

Rules:
- SELECT or WITH only. Never INSERT/UPDATE/DELETE/DROP/ATTACH/COPY/CREATE.
- Use only tables from this allowlist: {tables}.
- Use LOWER(x) for case-insensitive comparisons. Suburb names are mixed case.
- Use parameterless literals — no placeholders, no `?`, no `$1`.
- Always include `LIMIT N` (no more than 100). Aggregations should still use LIMIT.
- Output AUD amounts as plain numbers, not strings.
- The `interpretation` field is 1-2 sentences, plain English, ready to show
  the end user.
"""


def _schema_block() -> str:
    parts: list[str] = []
    for table in ALLOWED_TABLES:
        try:
            cols = describe_table(table)
        except Exception:  # noqa: BLE001
            continue
        if not cols:
            continue
        col_lines = ", ".join(f"{c['column']} ({c['type']})" for c in cols)
        parts.append(f"- {table}: {col_lines}")
    return "\n".join(parts)


@lru_cache(maxsize=1)
def _system_prompt() -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        schema=_schema_block(),
        tables=", ".join(sorted(ALLOWED_TABLES)),
    )


def _interpret_no_llm(question: str) -> _Draft:
    """Fallback that returns a representative query for the demo."""
    return _Draft(
        sql=(
            "SELECT suburb, COUNT(*) AS sales, AVG(price)::INT AS avg_price "
            "FROM properties WHERE price IS NOT NULL "
            "GROUP BY suburb ORDER BY avg_price DESC LIMIT 10"
        ),
        interpretation=(
            "(No LLM available) Returning the top 10 suburbs by average sale price "
            f"as a representative answer to: {question!r}."
        ),
    )


async def _ask_llm(question: str, retry_with: str | None = None) -> _Draft:
    messages: list[dict[str, str]] = [
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": f"Question: {question}"},
    ]
    if retry_with:
        messages.append({
            "role": "user",
            "content": (
                "Your previous SQL failed validation: "
                f"{retry_with}. Generate a corrected query."
            ),
        })
    return chat_structured(messages=messages, response_model=_Draft, temperature=0)


async def run(state: GraphState, inputs: dict[str, Any]) -> DataQueryResult:
    question = (inputs or {}).get("question") or state.user_message

    if settings.llm_provider == "azure" and not settings.azure_openai_api_key:
        draft = _interpret_no_llm(question)
    else:
        try:
            draft = await _ask_llm(question)
        except Exception as exc:  # noqa: BLE001
            log.warning("data_query LLM call failed (%s) — using fallback query", exc)
            draft = _interpret_no_llm(question)

    await emit("tool_call", {"node": "data_query", "tool": "duckdb_query", "args": {"sql": draft.sql}})

    outcome = validate(draft.sql)
    if not outcome.ok and settings.azure_openai_api_key:
        # Retry once with the validator errors as feedback
        await emit("tool_result", {
            "node": "data_query",
            "tool": "sql_validator",
            "preview": f"rejected: {', '.join(outcome.errors)} — retrying once",
        })
        try:
            draft = await _ask_llm(question, retry_with=", ".join(outcome.errors))
            outcome = validate(draft.sql)
        except Exception as exc:  # noqa: BLE001
            log.warning("data_query retry failed (%s)", exc)

    if not outcome.ok:
        await emit("tool_result", {
            "node": "data_query",
            "tool": "sql_validator",
            "preview": f"validation failed: {', '.join(outcome.errors)}",
        })
        return DataQueryResult(
            sql=draft.sql,
            columns=[],
            rows=[],
            row_count=0,
            interpretation=draft.interpretation,
            validation_passed=False,
            validation_errors=outcome.errors,
        )

    try:
        columns, rows = fetch_rows(outcome.sql)
    except Exception as exc:  # noqa: BLE001
        log.warning("data_query execution failed (%s)", exc)
        await emit("tool_result", {"node": "data_query", "tool": "duckdb_query",
                                    "preview": f"execution failed: {exc}"})
        return DataQueryResult(
            sql=outcome.sql,
            columns=[],
            rows=[],
            row_count=0,
            interpretation=draft.interpretation,
            validation_passed=True,
            validation_errors=[str(exc)],
        )

    # Coerce non-JSON-friendly types (Decimal, datetime) for the SSE payload
    safe_rows = [[_safe(v) for v in r] for r in rows]
    await emit("tool_result", {
        "node": "data_query",
        "tool": "duckdb_query",
        "preview": f"{len(safe_rows)} row(s) over {len(columns)} column(s)",
    })

    return DataQueryResult(
        sql=outcome.sql,
        columns=columns,
        rows=safe_rows,
        row_count=len(safe_rows),
        interpretation=draft.interpretation,
        validation_passed=True,
    )


def _safe(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (str, int, float, bool)):
        return v
    return str(v)
