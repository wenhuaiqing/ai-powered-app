"""Build the platform DuckDB from misc/ CSVs + synthetic listings/leads.

Run from repo root:
    uv run python scripts/build_db.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
MISC = REPO_ROOT / "misc"
DATA = REPO_ROOT / "data"
DB_PATH = DATA / "platform.duckdb"

RNG = np.random.default_rng(42)


def _money_to_float(s: object) -> float | None:
    if pd.isna(s):
        return None
    text = str(s).strip()
    if not text or text in {"-", "N/A", "n/a"}:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", text)
    if not cleaned or cleaned in {".", "-"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _percent_to_float(s: object) -> float | None:
    if pd.isna(s):
        return None
    text = str(s).strip().replace("%", "")
    if not text or text in {"-", "N/A", "n/a"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _int_or_none(s: object) -> int | None:
    if pd.isna(s):
        return None
    text = str(s).strip().replace(",", "")
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def load_properties() -> pd.DataFrame:
    path = MISC / "domain_properties.csv"
    df = pd.read_csv(path)
    df["date_sold"] = pd.to_datetime(df["date_sold"], format="%d/%m/%y", errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["property_size"] = pd.to_numeric(df["property_size"], errors="coerce")
    df = df.dropna(subset=["price", "suburb"]).reset_index(drop=True)
    df["property_id"] = [f"P{idx:05d}" for idx in range(len(df))]
    return df


def load_suburbs() -> pd.DataFrame:
    path = MISC / "Sydney Suburbs Reviews.csv"
    raw = pd.read_csv(path)
    df = pd.DataFrame({
        "name": raw["Name"].astype(str).str.strip(),
        "region": raw["Region"].astype(str).str.strip(),
        "population": raw["Population (rounded)*"].apply(_int_or_none),
        "postcode": raw["Postcode"].apply(_int_or_none),
        "ethnic_breakdown_2016": raw["Ethnic Breakdown 2016"].astype(str),
        "median_house_price_2020": raw["Median House Price (2020)"].apply(_money_to_float),
        "median_house_price_2021": raw["Median House Price (2021)"].apply(_money_to_float),
        "pct_change": raw["% Change"].apply(_percent_to_float),
        "median_house_rent_pw": raw["Median House Rent (per week)"].apply(_money_to_float),
        "median_apt_price_2020": raw["Median Apartment Price (2020)"].apply(_money_to_float),
        "median_apt_rent_pw": raw["Median Apartment Rent (per week)"].apply(_money_to_float),
        "public_housing_pct": raw["Public Housing %"].apply(_percent_to_float),
        "avg_years_held": pd.to_numeric(raw["Avg. Years Held"], errors="coerce"),
        "time_to_cbd_pt_min": pd.to_numeric(raw["Time to CBD (Public Transport) [Town Hall St]"], errors="coerce"),
        "time_to_cbd_drive_min": pd.to_numeric(raw["Time to CBD (Driving) [Town Hall St]"], errors="coerce"),
        "nearest_train_station": raw["Nearest Train Station"].astype(str),
        "highlights": raw["Highlights/Attractions"].astype(str),
        "ideal_for": raw["Ideal for"].astype(str),
        "traffic": pd.to_numeric(raw["Traffic"], errors="coerce"),
        "public_transport": pd.to_numeric(raw["Public Transport"], errors="coerce"),
        "affordability_rental": pd.to_numeric(raw["Affordability (Rental)"], errors="coerce"),
        "affordability_buying": pd.to_numeric(raw["Affordability (Buying)"], errors="coerce"),
        "nature": pd.to_numeric(raw["Nature"], errors="coerce"),
        "noise": pd.to_numeric(raw["Noise"], errors="coerce"),
        "things_to_see_do": raw["Things to See/Do"].astype(str),
        "family_friendliness": pd.to_numeric(raw["Family-Friendliness"], errors="coerce"),
        "pet_friendliness": pd.to_numeric(raw["Pet Friendliness"], errors="coerce"),
        "safety": pd.to_numeric(raw["Safety"], errors="coerce"),
        "overall_rating": pd.to_numeric(raw["Overall Rating"], errors="coerce"),
        "review_link": raw["Review Link"].astype(str),
    })
    df["name_lower"] = df["name"].str.lower()
    return df


def synthesise_listings(properties: pd.DataFrame, n: int = 60) -> pd.DataFrame:
    sample = properties.sample(n=n, random_state=42).reset_index(drop=True)
    stages = ["New", "Listed", "Under Offer", "Sold"]
    stage_weights = [0.2, 0.45, 0.2, 0.15]
    statuses = ["For Sale", "For Lease"]
    status_weights = [0.75, 0.25]
    sample["listing_id"] = [f"L{idx:04d}" for idx in range(len(sample))]
    sample["status"] = RNG.choice(statuses, size=len(sample), p=status_weights)
    sample["stage"] = RNG.choice(stages, size=len(sample), p=stage_weights)
    sample["listed_date"] = pd.Timestamp("2026-04-01") - pd.to_timedelta(
        RNG.integers(0, 90, size=len(sample)), unit="D"
    )
    sample["days_on_market"] = (pd.Timestamp("2026-05-22") - sample["listed_date"]).dt.days
    sample["agent_name"] = RNG.choice(
        ["Sarah Chen", "Tom O'Brien", "Priya Patel", "Marcus Tan", "Emma Wilson"],
        size=len(sample),
    )
    rent_factor = RNG.uniform(0.0008, 0.0014, size=len(sample))
    sample["asking_price"] = np.where(
        sample["status"] == "For Sale",
        (sample["price"] * RNG.uniform(0.96, 1.05, size=len(sample))).round(-3),
        (sample["price"] * rent_factor).round(0),
    )
    return sample


def synthesise_leads(suburbs: pd.DataFrame, n: int = 25) -> pd.DataFrame:
    suburb_names = suburbs["name"].sample(n=min(n, len(suburbs)), random_state=42).tolist()
    first_names = ["Alex", "Bella", "Cameron", "Daria", "Ethan", "Fiona", "Gita", "Hugo",
                   "Indira", "Jasper", "Kira", "Liam", "Maya", "Noah", "Olive", "Pari",
                   "Quinn", "Ravi", "Sienna", "Tarun", "Una", "Vikram", "Willa", "Xavier", "Yuki"]
    last_names = ["Nguyen", "Smith", "Patel", "Singh", "Kim", "Wong", "Brown", "Garcia",
                  "Wilson", "Lee", "Taylor", "Anderson", "Murphy", "O'Connor", "Tran"]
    intents = ["Buying", "Renting", "Selling appraisal"]
    intent_weights = [0.55, 0.3, 0.15]
    urgencies = ["low", "medium", "high"]
    leads = []
    for i in range(n):
        bed_min = int(RNG.integers(1, 5))
        suburb = suburb_names[i % len(suburb_names)]
        budget_low = int(RNG.choice([500_000, 700_000, 900_000, 1_100_000, 1_400_000, 1_800_000]))
        budget_high = int(budget_low * RNG.uniform(1.15, 1.45))
        leads.append({
            "lead_id": f"LD{i:04d}",
            "name": f"{RNG.choice(first_names)} {RNG.choice(last_names)}",
            "email": f"lead{i}@example.com",
            "phone": f"04{RNG.integers(10, 99)} {RNG.integers(100, 999)} {RNG.integers(100, 999)}",
            "intent": str(RNG.choice(intents, p=intent_weights)),
            "min_bed": bed_min,
            "min_bath": max(1, bed_min - 1),
            "min_parking": int(RNG.integers(0, 3)),
            "preferred_suburb": suburb,
            "max_km_from_cbd": int(RNG.choice([10, 15, 20, 25, 30, 40])),
            "budget_min": budget_low,
            "budget_max": budget_high,
            "urgency": str(RNG.choice(urgencies, p=[0.35, 0.45, 0.2])),
            "notes": _lead_note(bed_min, suburb),
            "created_date": (pd.Timestamp("2026-05-22") - pd.Timedelta(days=int(RNG.integers(0, 60)))).date().isoformat(),
        })
    return pd.DataFrame(leads)


def _lead_note(bed: int, suburb: str) -> str:
    hooks = [
        f"Looking for a {bed}-bed near {suburb}, family-friendly, good schools.",
        f"Wants quiet street in {suburb} area, walking distance to transport.",
        f"Open to {suburb} surrounds — prioritising natural light and a garden.",
        f"Prefers {suburb}; flexible on size if location is right.",
        f"Investment buyer eyeing {suburb} — yield over capital growth.",
    ]
    return str(RNG.choice(hooks))


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    print(f"Loading properties from {MISC / 'domain_properties.csv'}", flush=True)
    properties = load_properties()
    print(f"  loaded {len(properties):,} properties", flush=True)

    print(f"Loading suburb reviews from {MISC / 'Sydney Suburbs Reviews.csv'}", flush=True)
    suburbs = load_suburbs()
    print(f"  loaded {len(suburbs):,} suburbs", flush=True)

    print("Generating synthetic listings + leads", flush=True)
    listings = synthesise_listings(properties)
    leads = synthesise_leads(suburbs)
    print(f"  {len(listings)} listings, {len(leads)} leads", flush=True)

    print(f"Writing DuckDB at {DB_PATH}", flush=True)
    con = duckdb.connect(str(DB_PATH))
    con.register("df_properties", properties)
    con.register("df_suburbs", suburbs)
    con.register("df_listings", listings)
    con.register("df_leads", leads)
    con.execute("CREATE TABLE properties AS SELECT * FROM df_properties")
    con.execute("CREATE TABLE suburbs AS SELECT * FROM df_suburbs")
    con.execute("CREATE TABLE listings AS SELECT * FROM df_listings")
    con.execute("CREATE TABLE leads AS SELECT * FROM df_leads")

    # Convenience view joining listings to their backing property + suburb
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

    counts = con.execute("""
        SELECT 'properties' AS table_name, COUNT(*) AS n FROM properties
        UNION ALL SELECT 'suburbs', COUNT(*) FROM suburbs
        UNION ALL SELECT 'listings', COUNT(*) FROM listings
        UNION ALL SELECT 'leads', COUNT(*) FROM leads
    """).fetchall()
    con.close()

    print("Row counts:")
    for table, n in counts:
        print(f"  {table}: {n:,}")
    print(f"Done. DB at {DB_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"build_db failed: {exc}", file=sys.stderr)
        raise
