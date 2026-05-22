"""DuckDB connection helpers — single-process, single-file analytics DB."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Sequence

import duckdb

from src.settings import settings


@contextmanager
def get_conn() -> Iterator[duckdb.DuckDBPyConnection]:
    path = Path(settings.duckdb_path)
    if not path.exists():
        raise RuntimeError(
            f"DuckDB not found at {path}. Run `python scripts/build_db.py` first."
        )
    conn = duckdb.connect(str(path), read_only=True)
    try:
        yield conn
    finally:
        conn.close()


def fetch_rows(sql: str, params: Sequence[object] | None = None) -> tuple[list[str], list[list[object]]]:
    """Execute SELECT and return (columns, rows). Use parameter binding for user input."""
    with get_conn() as conn:
        cursor = conn.execute(sql, params or [])
        cols = [d[0] for d in cursor.description] if cursor.description else []
        rows = [list(r) for r in cursor.fetchall()]
    return cols, rows


def list_tables() -> list[str]:
    cols, rows = fetch_rows("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'")
    return [r[0] for r in rows]


def describe_table(name: str) -> list[dict[str, str]]:
    cols, rows = fetch_rows(
        "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = ?",
        [name],
    )
    return [{"column": r[0], "type": r[1]} for r in rows]
