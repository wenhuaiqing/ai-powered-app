"""Embed Sydney Suburbs Reviews into data/reviews_embeddings.parquet.

Each suburb becomes a single 'card' — descriptive prose plus key numeric
scores formatted as text — so queries like 'family-friendly quiet near
transport' can retrieve relevant suburbs by cosine similarity.

Run from repo root after build_db.py:
    uv run python scripts/build_review_embeddings.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import duckdb
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "platform.duckdb"
OUT_PATH = REPO_ROOT / "data" / "reviews_embeddings.parquet"

load_dotenv(REPO_ROOT / ".env")
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
EMBED_MODEL = os.getenv("AZURE_OPENAI_EMBED_MODEL", "text-embedding-3-small")


def _card(row: pd.Series) -> str:
    def opt(label: str, value: object, suffix: str = "") -> str:
        if value is None or (isinstance(value, float) and pd.isna(value)) or str(value).strip() in ("", "nan"):
            return ""
        return f"{label}: {value}{suffix}"

    parts = [
        f"Suburb: {row['name']} ({row['region']}, postcode {row['postcode']})",
        opt("Highlights", row.get("highlights")),
        opt("Ideal for", row.get("ideal_for")),
        opt("Things to see/do", row.get("things_to_see_do")),
        opt("Family-friendliness", row.get("family_friendliness"), "/10"),
        opt("Safety", row.get("safety"), "/10"),
        opt("Pet-friendliness", row.get("pet_friendliness"), "/10"),
        opt("Public transport", row.get("public_transport"), "/10"),
        opt("Affordability (buying)", row.get("affordability_buying"), "/10"),
        opt("Affordability (rental)", row.get("affordability_rental"), "/10"),
        opt("Nature", row.get("nature"), "/10"),
        opt("Noise", row.get("noise"), "/10"),
        opt("Traffic", row.get("traffic"), "/10"),
        opt("Overall rating", row.get("overall_rating"), "/10"),
        opt("Median house price 2021", f"${row['median_house_price_2021']:,.0f}" if pd.notna(row.get("median_house_price_2021")) else None),
        opt("Median house rent per week", f"${row['median_house_rent_pw']:,.0f}" if pd.notna(row.get("median_house_rent_pw")) else None),
        opt("Time to CBD (public transport)", row.get("time_to_cbd_pt_min"), " min"),
        opt("Time to CBD (driving)", row.get("time_to_cbd_drive_min"), " min"),
        opt("Nearest train station", row.get("nearest_train_station")),
    ]
    return "\n".join(p for p in parts if p)


def embed_batch(client: OpenAI, texts: list[str]) -> list[list[float]]:
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]


def main() -> None:
    if not AZURE_ENDPOINT or not AZURE_API_KEY:
        print("AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY not set — cannot build embeddings.",
              file=sys.stderr)
        sys.exit(1)
    if not DB_PATH.exists():
        print(f"DuckDB not found at {DB_PATH}. Run scripts/build_db.py first.", file=sys.stderr)
        sys.exit(1)

    con = duckdb.connect(str(DB_PATH), read_only=True)
    suburbs = con.execute("SELECT * FROM suburbs").df()
    con.close()
    suburbs["card"] = suburbs.apply(_card, axis=1)
    print(f"Built {len(suburbs)} suburb cards", flush=True)

    client = OpenAI(base_url=AZURE_ENDPOINT, api_key=AZURE_API_KEY)
    BATCH = 32
    embeddings: list[list[float]] = []
    cards = suburbs["card"].tolist()
    for i in range(0, len(cards), BATCH):
        batch = cards[i:i + BATCH]
        attempt = 0
        while True:
            try:
                embeddings.extend(embed_batch(client, batch))
                break
            except Exception as exc:  # noqa: BLE001
                attempt += 1
                if attempt > 3:
                    raise
                wait = 2 ** attempt
                print(f"  batch {i//BATCH} failed ({exc}); retry {attempt} after {wait}s", flush=True)
                time.sleep(wait)
        print(f"  embedded {i + len(batch)}/{len(cards)}", flush=True)

    out_df = suburbs[[
        "name", "region", "postcode", "family_friendliness", "safety",
        "public_transport", "affordability_buying", "median_house_price_2021",
        "time_to_cbd_pt_min", "card",
    ]].copy()
    out_df["embedding"] = embeddings
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_parquet(OUT_PATH, index=False)
    print(f"Wrote {len(out_df)} suburb embeddings to {OUT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"build_review_embeddings failed: {exc}", file=sys.stderr)
        raise
