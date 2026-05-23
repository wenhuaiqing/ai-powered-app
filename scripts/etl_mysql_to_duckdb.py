"""Pipeline: MySQL (OLTP) -> DuckDB (OLAP).

Extracts the relational source-of-truth from MySQL, denormalises it, and
writes the analytical tables that power /api/insights, /api/valuations,
the Data Query agent, and the Matcher agent.

Idempotent: drops + recreates the analytical tables on every run. Safe to
schedule (cron / EventBridge) or invoke ad-hoc after writes land.

Run from repo root:
    uv run python scripts/etl_mysql_to_duckdb.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import duckdb
import pandas as pd
from sqlalchemy import create_engine, text

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data"
DB_PATH = DATA / "platform.duckdb"


def _engine_url() -> str:
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT", "3306")
    user = os.getenv("MYSQL_USER", "app")
    password = os.getenv("MYSQL_PASSWORD", "app")
    db = os.getenv("MYSQL_DATABASE", "reapit_demo")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}?charset=utf8mb4"


def _extract(engine) -> dict[str, pd.DataFrame]:
    with engine.connect() as conn:
        suburbs = pd.read_sql(text("SELECT * FROM suburbs"), conn)
        properties = pd.read_sql(text("SELECT * FROM properties"), conn)
        listings = pd.read_sql(text("""
            SELECT l.*, a.name AS agent_name
            FROM listings l
            LEFT JOIN agents a ON a.agent_id = l.agent_id
        """), conn)
        leads = pd.read_sql(text("""
            SELECT le.*, a.name AS assigned_agent_name
            FROM leads le
            LEFT JOIN agents a ON a.agent_id = le.assigned_agent_id
        """), conn)
    return {"suburbs": suburbs, "properties": properties, "listings": listings, "leads": leads}


def _transform(extracts: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    properties = extracts["properties"].rename(columns={"property_type": "type"})
    return {
        "suburbs": extracts["suburbs"],
        "properties": properties,
        "listings": extracts["listings"],
        "leads": extracts["leads"],
    }


def _load(tables: dict[str, pd.DataFrame]) -> dict[str, int]:
    DATA.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = duckdb.connect(str(DB_PATH))

    for name, df in tables.items():
        con.register(f"df_{name}", df)
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM df_{name}")
        con.unregister(f"df_{name}")

    con.execute("""
        CREATE VIEW listings_enriched AS
        SELECT
            l.listing_id,
            l.status,
            l.stage,
            l.asking_price,
            l.listed_date,
            l.days_on_market,
            l.agent_name,
            p.property_id,
            p.suburb,
            p.num_bed,
            p.num_bath,
            p.num_parking,
            p.property_size,
            p.type,
            p.km_from_cbd,
            p.suburb_lat,
            p.suburb_lng,
            s.region,
            s.median_house_price_2021,
            s.median_house_rent_pw,
            s.family_friendliness,
            s.safety
        FROM listings l
        JOIN properties p ON l.property_id = p.property_id
        LEFT JOIN suburbs s ON LOWER(s.name) = LOWER(p.suburb)
    """)

    counts = {
        name: con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        for name in tables
    }
    con.close()
    return counts


def main() -> None:
    engine = create_engine(_engine_url(), future=True)

    print("Extracting from MySQL", flush=True)
    extracts = _extract(engine)
    for name, df in extracts.items():
        print(f"  {name}: {len(df):,} rows")

    print("Transforming", flush=True)
    transformed = _transform(extracts)

    print(f"Loading into DuckDB at {DB_PATH}", flush=True)
    counts = _load(transformed)

    print("ETL done. Row counts (DuckDB):")
    for tbl, n in counts.items():
        print(f"  {tbl}: {n:,}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"etl_mysql_to_duckdb failed: {exc}", file=sys.stderr)
        raise
