"""Apply pending MySQL schema migrations from scripts/migrations/.

Numbered SQL files run in order. The `schema_migrations` table tracks
which ones have already been applied — safe to re-run anytime.

Run from repo root:
    uv run python scripts/migrate_mysql.py
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = REPO_ROOT / "scripts" / "migrations"
MIGRATION_PATTERN = re.compile(r"^(\d{4})_[\w]+\.sql$")


def _engine_url() -> str:
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT", "3306")
    user = os.getenv("MYSQL_USER", "app")
    password = os.getenv("MYSQL_PASSWORD", "app")
    db = os.getenv("MYSQL_DATABASE", "reapit_demo")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}?charset=utf8mb4"


def _split_statements(sql: str) -> list[str]:
    # MySQL doesn't like multi-statement execution through SQLAlchemy by
    # default. Split on semicolons that aren't inside string literals.
    stmts: list[str] = []
    buf = []
    in_string: str | None = None
    for ch in sql:
        if in_string:
            buf.append(ch)
            if ch == in_string:
                in_string = None
            continue
        if ch in ("'", '"', "`"):
            in_string = ch
            buf.append(ch)
            continue
        if ch == ";":
            stmt = "".join(buf).strip()
            if stmt:
                stmts.append(stmt)
            buf = []
            continue
        buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        stmts.append(tail)
    return stmts


def _discover_migrations() -> list[tuple[str, Path]]:
    if not MIGRATIONS_DIR.is_dir():
        return []
    items: list[tuple[str, Path]] = []
    for path in sorted(MIGRATIONS_DIR.iterdir()):
        m = MIGRATION_PATTERN.match(path.name)
        if not m:
            continue
        items.append((path.stem, path))
    return items


def main() -> None:
    engine = create_engine(_engine_url(), future=True)

    # Bootstrap the tracking table without going through the migrations
    # themselves (the first migration also CREATEs it — idempotent).
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(64) PRIMARY KEY,
                applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """))
        applied = {row[0] for row in conn.execute(text("SELECT version FROM schema_migrations"))}

    migrations = _discover_migrations()
    if not migrations:
        print("No migrations found under scripts/migrations/")
        return

    pending = [(v, p) for v, p in migrations if v not in applied]
    if not pending:
        print(f"All {len(migrations)} migrations already applied.")
        return

    print(f"Applying {len(pending)} migration(s):")
    for version, path in pending:
        print(f"  -> {version} ({path.name})", flush=True)
        sql = path.read_text(encoding="utf-8")
        statements = _split_statements(sql)
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))
            conn.execute(
                text("INSERT INTO schema_migrations(version) VALUES (:v)"),
                {"v": version},
            )
        print(f"     ok ({len(statements)} statements)")
    print(f"Done. Applied {len(pending)} new migration(s).")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"migrate_mysql failed: {exc}", file=sys.stderr)
        raise
