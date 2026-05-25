"""MySQL connection helpers. OLTP source-of-truth for properties + leads.

Engine is constructed lazily (so unit tests + offline runs don't try to
connect on import). Pool tuned for a single Fargate task — a handful of
concurrent SSE handlers, not high-throughput.
"""

from __future__ import annotations

import datetime as _dt
import logging
from contextlib import contextmanager
from decimal import Decimal
from functools import lru_cache
from typing import Any, Iterator, Mapping, Sequence

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import CursorResult

from src.settings import settings

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Cached SQLAlchemy engine. One per process."""
    return create_engine(
        settings.mysql_url,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
        pool_recycle=1800,
        future=True,
    )


@contextmanager
def connection() -> Iterator[Any]:
    engine = get_engine()
    with engine.connect() as conn:
        yield conn


def fetch_all(
    sql: str,
    params: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
) -> tuple[list[str], list[list[Any]]]:
    """Execute SELECT and return (columns, rows)."""
    with connection() as conn:
        result: CursorResult = conn.execute(text(sql), params or {})
        cols = list(result.keys())
        rows = [list(r) for r in result.fetchall()]
    return cols, rows


def fetch_one(
    sql: str,
    params: Mapping[str, Any] | None = None,
) -> tuple[list[str], list[Any]] | None:
    cols, rows = fetch_all(sql, params)
    if not rows:
        return None
    return cols, rows[0]


def execute(
    sql: str,
    params: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
) -> int:
    """Execute INSERT/UPDATE/DELETE, returns lastrowid (0 if not applicable)."""
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(text(sql), params or {})
        return int(result.lastrowid or 0)


def _coerce(value: Any) -> Any:
    """Normalise types at the API boundary.

    - Decimal -> float (FastAPI's encoder otherwise stringifies them,
      and agents call int() on those strings and blow up).
    - datetime -> ISO string with a `Z` suffix (MySQL DATETIME columns
      are timezone-naive and the server runs in UTC, so tagging Z lets
      the browser convert to local time correctly).
    - date -> ISO date string.
    """
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, _dt.datetime):
        return value.isoformat() + "Z"
    if isinstance(value, _dt.date):
        return value.isoformat()
    return value


def rows_to_dicts(cols: list[str], rows: list[list[Any]]) -> list[dict[str, Any]]:
    return [{c: _coerce(v) for c, v in zip(cols, r)} for r in rows]
