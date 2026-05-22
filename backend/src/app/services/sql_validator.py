"""Validator for LLM-generated DuckDB SQL. SELECT-only, allowlisted tables, LIMIT injected.

Mirrors mcnab-data-app/services/ai/sql_validator.py but targets DuckDB and a
fixed table allowlist for the demo schema.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

ALLOWED_TABLES = {
    "properties",
    "suburbs",
    "listings",
    "leads",
    "listings_enriched",
}

# DDL/DML keywords that must NEVER appear in a generated query.
FORBIDDEN_KEYWORDS = {
    "insert", "update", "delete", "drop", "truncate", "alter", "create",
    "attach", "detach", "copy", "export", "import", "pragma", "set", "call",
    "grant", "revoke", "merge", "vacuum",
}

DEFAULT_LIMIT = 100
MAX_LIMIT = 500


@dataclass
class ValidationOutcome:
    ok: bool
    sql: str          # post-rewrite SQL ready to execute (or the original on failure)
    errors: list[str]
    tables_referenced: list[str]


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"--[^\n]*", "", sql)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return sql


def _statement_count(sql: str) -> int:
    # Count top-level semicolons (ignoring those inside strings is overkill for
    # a demo — the LLM rarely produces string literals containing ; here).
    cleaned = sql.strip().rstrip(";")
    return cleaned.count(";") + 1 if cleaned else 0


def _extract_tables(sql: str) -> set[str]:
    # Match FROM <name> and JOIN <name>, optionally schema-qualified. Strip
    # quoting. Good enough for the demo allowlist check.
    pattern = re.compile(r"\b(?:from|join)\s+([\"`\w\.]+)", re.IGNORECASE)
    tables: set[str] = set()
    for match in pattern.finditer(sql):
        raw = match.group(1).strip().strip('"').strip("`")
        # Take the last segment of a dotted name (e.g. schema.table -> table)
        last = raw.split(".")[-1]
        tables.add(last.lower())
    return tables


def _has_limit(sql: str) -> bool:
    return re.search(r"\blimit\s+\d+", sql, re.IGNORECASE) is not None


def _inject_limit(sql: str, limit: int) -> str:
    stripped = sql.rstrip().rstrip(";")
    return f"{stripped}\nLIMIT {limit}"


def validate(sql: str) -> ValidationOutcome:
    errors: list[str] = []

    if not sql or not sql.strip():
        return ValidationOutcome(ok=False, sql=sql, errors=["empty SQL"], tables_referenced=[])

    cleaned = _strip_comments(sql).strip().rstrip(";")
    lowered = cleaned.lower()

    if _statement_count(cleaned) > 1:
        errors.append("multiple statements are not allowed")

    if not lowered.lstrip("(").startswith(("select", "with")):
        errors.append("only SELECT/WITH queries are allowed")

    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", lowered):
            errors.append(f"forbidden keyword: {kw}")

    tables = _extract_tables(cleaned)
    not_allowed = sorted(t for t in tables if t not in ALLOWED_TABLES)
    if not_allowed:
        errors.append(f"table(s) not in allowlist: {', '.join(not_allowed)}")

    if errors:
        return ValidationOutcome(ok=False, sql=sql, errors=errors, tables_referenced=sorted(tables))

    final_sql = cleaned
    if not _has_limit(final_sql):
        final_sql = _inject_limit(final_sql, DEFAULT_LIMIT)
    else:
        # Clamp any explicit LIMIT above the ceiling
        def clamp(match: re.Match[str]) -> str:
            n = int(match.group(1))
            return f"LIMIT {min(n, MAX_LIMIT)}"
        final_sql = re.sub(r"\bLIMIT\s+(\d+)", clamp, final_sql, flags=re.IGNORECASE)

    return ValidationOutcome(ok=True, sql=final_sql, errors=[], tables_referenced=sorted(tables))
