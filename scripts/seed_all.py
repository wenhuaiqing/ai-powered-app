"""One-shot orchestrator: migrate -> build MySQL -> ETL to DuckDB.

This is what the AWS seed task runs. Locally it's also the easy "do
everything from a clean MySQL" command.

Run from repo root (MySQL must be reachable):
    uv run python scripts/seed_all.py
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
STEPS = [
    SCRIPTS / "migrate_mysql.py",
    SCRIPTS / "build_mysql.py",
    SCRIPTS / "etl_mysql_to_duckdb.py",
]


def main() -> None:
    for step in STEPS:
        print(f"\n=== {step.name} ===", flush=True)
        runpy.run_path(str(step), run_name="__main__")
    print("\nSeed pipeline done.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"seed_all failed: {exc}", file=sys.stderr)
        sys.exit(1)
