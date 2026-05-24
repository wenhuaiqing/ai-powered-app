"""Load CSV source data into MySQL (OLTP).

Runs after `migrate_mysql.py`. Truncates + reloads — idempotent.
The synthesised listings + leads use the same RNG seed as build_db.py so
the IDs match across MySQL and the legacy DuckDB build.

Run from repo root (MySQL must be up — `docker compose up -d mysql`):
    uv run python scripts/build_mysql.py
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

REPO_ROOT = Path(__file__).resolve().parent.parent
MISC = REPO_ROOT / "misc"

RNG = np.random.default_rng(42)


def _engine_url() -> str:
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT", "3306")
    user = os.getenv("MYSQL_USER", "app")
    password = os.getenv("MYSQL_PASSWORD", "app")
    db = os.getenv("MYSQL_DATABASE", "reapit_demo")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}?charset=utf8mb4&local_infile=1"


def _money_to_float(s: object) -> float | None:
    if pd.isna(s):
        return None
    text_ = str(s).strip()
    if not text_ or text_ in {"-", "N/A", "n/a"}:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", text_)
    if not cleaned or cleaned in {".", "-"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _percent_to_float(s: object) -> float | None:
    if pd.isna(s):
        return None
    text_ = str(s).strip().replace("%", "")
    if not text_ or text_ in {"-", "N/A", "n/a"}:
        return None
    try:
        return float(text_)
    except ValueError:
        return None


def _int_or_none(s: object) -> int | None:
    if pd.isna(s):
        return None
    text_ = str(s).strip().replace(",", "")
    if not text_:
        return None
    try:
        return int(float(text_))
    except ValueError:
        return None


def load_properties() -> pd.DataFrame:
    df = pd.read_csv(MISC / "domain_properties.csv")
    df["date_sold"] = pd.to_datetime(df["date_sold"], format="%d/%m/%y", errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["property_size"] = pd.to_numeric(df["property_size"], errors="coerce")
    df = df.dropna(subset=["price", "suburb"]).reset_index(drop=True)
    df["property_id"] = [f"P{idx:05d}" for idx in range(len(df))]
    out = pd.DataFrame({
        "property_id":              df["property_id"],
        "suburb":                   df["suburb"].astype(str),
        "postcode":                 df.get("postcode"),
        "price":                    df["price"],
        "property_type":            df.get("type"),
        "num_bed":                  df.get("num_bed"),
        "num_bath":                 df.get("num_bath"),
        "num_parking":              df.get("num_parking"),
        "property_size":            df["property_size"],
        "suburb_population":        df.get("suburb_population"),
        "suburb_median_income":     df.get("suburb_median_income"),
        "suburb_sqkm":              df.get("suburb_sqkm"),
        "suburb_elevation":         df.get("suburb_elevation"),
        "cash_rate":                df.get("cash_rate"),
        "property_inflation_index": df.get("property_inflation_index"),
        "km_from_cbd":              df.get("km_from_cbd"),
        "suburb_lat":               df.get("suburb_lat"),
        "suburb_lng":               df.get("suburb_lng"),
        "date_sold":                df["date_sold"].dt.date,
    })
    return out


def load_suburbs() -> pd.DataFrame:
    raw = pd.read_csv(MISC / "Sydney Suburbs Reviews.csv")
    df = pd.DataFrame({
        "name":                       raw["Name"].astype(str).str.strip(),
        "region":                     raw["Region"].astype(str).str.strip(),
        "population":                 raw["Population (rounded)*"].apply(_int_or_none),
        "postcode":                   raw["Postcode"].apply(_int_or_none),
        "median_house_price_2020":    raw["Median House Price (2020)"].apply(_money_to_float),
        "median_house_price_2021":    raw["Median House Price (2021)"].apply(_money_to_float),
        "pct_change":                 raw["% Change"].apply(_percent_to_float),
        "median_house_rent_pw":       raw["Median House Rent (per week)"].apply(_money_to_float),
        "median_apt_price_2020":      raw["Median Apartment Price (2020)"].apply(_money_to_float),
        "median_apt_rent_pw":         raw["Median Apartment Rent (per week)"].apply(_money_to_float),
        "public_housing_pct":         raw["Public Housing %"].apply(_percent_to_float),
        "avg_years_held":             pd.to_numeric(raw["Avg. Years Held"], errors="coerce"),
        "time_to_cbd_pt_min":         pd.to_numeric(raw["Time to CBD (Public Transport) [Town Hall St]"], errors="coerce"),
        "time_to_cbd_drive_min":      pd.to_numeric(raw["Time to CBD (Driving) [Town Hall St]"], errors="coerce"),
        "nearest_train_station":      raw["Nearest Train Station"].astype(str),
        "highlights":                 raw["Highlights/Attractions"].astype(str),
        "ideal_for":                  raw["Ideal for"].astype(str),
        "traffic":                    pd.to_numeric(raw["Traffic"], errors="coerce"),
        "public_transport":           pd.to_numeric(raw["Public Transport"], errors="coerce"),
        "affordability_rental":       pd.to_numeric(raw["Affordability (Rental)"], errors="coerce"),
        "affordability_buying":       pd.to_numeric(raw["Affordability (Buying)"], errors="coerce"),
        "nature":                     pd.to_numeric(raw["Nature"], errors="coerce"),
        "noise":                      pd.to_numeric(raw["Noise"], errors="coerce"),
        "things_to_see_do":           raw["Things to See/Do"].astype(str),
        "family_friendliness":        pd.to_numeric(raw["Family-Friendliness"], errors="coerce"),
        "pet_friendliness":           pd.to_numeric(raw["Pet Friendliness"], errors="coerce"),
        "safety":                     pd.to_numeric(raw["Safety"], errors="coerce"),
        "overall_rating":             pd.to_numeric(raw["Overall Rating"], errors="coerce"),
        "review_link":                raw["Review Link"].astype(str),
    })
    return df


AGENTS = [
    ("A001", "Sarah Chen",   "sarah.chen@reapit-demo.au"),
    ("A002", "Tom O'Brien",  "tom.obrien@reapit-demo.au"),
    ("A003", "Priya Patel",  "priya.patel@reapit-demo.au"),
    ("A004", "Marcus Tan",   "marcus.tan@reapit-demo.au"),
    ("A005", "Emma Wilson",  "emma.wilson@reapit-demo.au"),
]


def synthesise_listings(properties: pd.DataFrame, n: int = 60) -> pd.DataFrame:
    sample = properties.sample(n=n, random_state=42).reset_index(drop=True)
    stages = ["New", "Listed", "Under Offer", "Sold"]
    stage_weights = [0.2, 0.45, 0.2, 0.15]
    statuses = ["For Sale", "For Lease"]
    status_weights = [0.75, 0.25]
    agent_ids = [a[0] for a in AGENTS]

    listed = pd.Timestamp("2026-04-01") - pd.to_timedelta(
        RNG.integers(0, 90, size=len(sample)), unit="D"
    )
    days_on_market = (pd.Timestamp("2026-05-22") - listed).days
    rent_factor = RNG.uniform(0.0008, 0.0014, size=len(sample))
    statuses_arr = RNG.choice(statuses, size=len(sample), p=status_weights)
    asking = np.where(
        statuses_arr == "For Sale",
        (sample["price"].to_numpy() * RNG.uniform(0.96, 1.05, size=len(sample))).round(-3),
        (sample["price"].to_numpy() * rent_factor).round(0),
    )
    return pd.DataFrame({
        "listing_id":     [f"L{idx:04d}" for idx in range(len(sample))],
        "property_id":    sample["property_id"].values,
        "status":         statuses_arr,
        "stage":          RNG.choice(stages, size=len(sample), p=stage_weights),
        "asking_price":   asking,
        "listed_date":    listed.date,
        "days_on_market": days_on_market,
        "agent_id":       RNG.choice(agent_ids, size=len(sample)),
        "headline":       None,
        "body_markdown":  None,
    })


def synthesise_leads(suburbs: pd.DataFrame, n: int = 25) -> pd.DataFrame:
    suburb_names = suburbs["name"].sample(n=min(n, len(suburbs)), random_state=42).tolist()
    first_names = ["Alex","Bella","Cameron","Daria","Ethan","Fiona","Gita","Hugo",
                   "Indira","Jasper","Kira","Liam","Maya","Noah","Olive","Pari",
                   "Quinn","Ravi","Sienna","Tarun","Una","Vikram","Willa","Xavier","Yuki"]
    last_names = ["Nguyen","Smith","Patel","Singh","Kim","Wong","Brown","Garcia",
                  "Wilson","Lee","Taylor","Anderson","Murphy","O'Connor","Tran"]
    intents = ["Buying","Renting","Selling appraisal"]
    intent_weights = [0.55, 0.3, 0.15]
    urgencies = ["low","medium","high"]
    statuses = ["New","Contacted","Qualified","Viewed"]
    status_weights = [0.40, 0.30, 0.20, 0.10]
    agent_ids = [a[0] for a in AGENTS]

    rows = []
    for i in range(n):
        bed_min = int(RNG.integers(1, 5))
        suburb = suburb_names[i % len(suburb_names)]
        budget_low = int(RNG.choice([500_000, 700_000, 900_000, 1_100_000, 1_400_000, 1_800_000]))
        budget_high = int(budget_low * RNG.uniform(1.15, 1.45))
        rows.append({
            "lead_id":          f"LD{i:04d}",
            "name":             f"{RNG.choice(first_names)} {RNG.choice(last_names)}",
            "email":            f"lead{i}@example.com",
            "phone":            f"04{RNG.integers(10, 99)} {RNG.integers(100, 999)} {RNG.integers(100, 999)}",
            "intent":           str(RNG.choice(intents, p=intent_weights)),
            "status":           str(RNG.choice(statuses, p=status_weights)),
            "min_bed":          bed_min,
            "min_bath":         max(1, bed_min - 1),
            "min_parking":      int(RNG.integers(0, 3)),
            "preferred_suburb": suburb,
            "max_km_from_cbd":  int(RNG.choice([10, 15, 20, 25, 30, 40])),
            "budget_min":       budget_low,
            "budget_max":       budget_high,
            "urgency":          str(RNG.choice(urgencies, p=[0.35, 0.45, 0.2])),
            "notes":            _lead_note(bed_min, suburb),
            "assigned_agent_id": str(RNG.choice(agent_ids)),
            "created_date":     (pd.Timestamp("2026-05-22") - pd.Timedelta(days=int(RNG.integers(0, 60)))).date(),
        })
    return pd.DataFrame(rows)


def _lead_note(bed: int, suburb: str) -> str:
    hooks = [
        f"Looking for a {bed}-bed near {suburb}, family-friendly, good schools.",
        f"Wants quiet street in {suburb} area, walking distance to transport.",
        f"Open to {suburb} surrounds — prioritising natural light and a garden.",
        f"Prefers {suburb}; flexible on size if location is right.",
        f"Investment buyer eyeing {suburb} — yield over capital growth.",
    ]
    return str(RNG.choice(hooks))


def _truncate(conn, tables: list[str]) -> None:
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
    for tbl in tables:
        conn.execute(text(f"TRUNCATE TABLE {tbl}"))
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


def main() -> None:
    engine = create_engine(_engine_url(), future=True)

    print("Loading source CSVs", flush=True)
    properties = load_properties()
    suburbs = load_suburbs()
    print(f"  {len(properties):,} properties, {len(suburbs):,} suburbs")

    print("Synthesising listings + leads", flush=True)
    listings = synthesise_listings(properties)
    leads = synthesise_leads(suburbs)
    print(f"  {len(listings)} listings, {len(leads)} leads")

    with engine.begin() as conn:
        _truncate(conn, ["agent_runs", "lead_events", "listings", "leads", "agents", "properties", "suburbs"])

        conn.execute(
            text("INSERT INTO agents(agent_id, name, email) VALUES (:agent_id, :name, :email)"),
            [{"agent_id": a[0], "name": a[1], "email": a[2]} for a in AGENTS],
        )

        suburbs.to_sql("suburbs", conn, if_exists="append", index=False, chunksize=500)
        properties.to_sql("properties", conn, if_exists="append", index=False, chunksize=2000)
        listings.to_sql("listings", conn, if_exists="append", index=False, chunksize=500)
        leads.to_sql("leads", conn, if_exists="append", index=False, chunksize=500)

        # Seed a couple of lead_events so the audit log isn't empty in demos.
        seeded_events = []
        for lead_id in leads["lead_id"].head(8):
            seeded_events.append({
                "lead_id": lead_id,
                "event_type": "status_change",
                "from_status": "New",
                "to_status": "Contacted",
                "note": "Initial outreach call",
                "actor": "system-seed",
            })
        conn.execute(
            text("""INSERT INTO lead_events(lead_id, event_type, from_status, to_status, note, actor)
                    VALUES (:lead_id, :event_type, :from_status, :to_status, :note, :actor)"""),
            seeded_events,
        )

        counts = conn.execute(text("""
            SELECT 'agents'      AS t, COUNT(*) FROM agents
            UNION ALL SELECT 'suburbs',    COUNT(*) FROM suburbs
            UNION ALL SELECT 'properties', COUNT(*) FROM properties
            UNION ALL SELECT 'listings',   COUNT(*) FROM listings
            UNION ALL SELECT 'leads',      COUNT(*) FROM leads
            UNION ALL SELECT 'lead_events',COUNT(*) FROM lead_events
        """)).all()

    print("Row counts (MySQL):")
    for tbl, n in counts:
        print(f"  {tbl}: {n:,}")
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"build_mysql failed: {exc}", file=sys.stderr)
        raise
