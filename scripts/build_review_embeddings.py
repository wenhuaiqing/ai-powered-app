"""Embed Sydney Suburbs Reviews into data/reviews_embeddings.parquet.

Each suburb becomes a single 'card' -- descriptive prose plus key numeric
scores -- so queries like "family-friendly quiet near transport" can
retrieve relevant suburbs by cosine similarity.

Uses Bedrock Titan v2 (1024-D) via boto3. Needs AWS creds on PATH
(`aws configure` or env vars) + Bedrock model access enabled in the
target region.

Run from repo root after build_db.py:
    uv run python scripts/build_review_embeddings.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "platform.duckdb"
OUT_PATH = REPO_ROOT / "data" / "reviews_embeddings.parquet"

# Make the backend importable so we reuse the same Titan wrapper the
# RAG retriever uses at request time -- guarantees identical
# normalisation + dimensions between corpus and query.
sys.path.insert(0, str(REPO_ROOT / "backend"))
from src.app.services import embed  # noqa: E402


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


def main() -> None:
    if not DB_PATH.exists():
        print(f"DuckDB not found at {DB_PATH}. Run scripts/build_db.py first.", file=sys.stderr)
        sys.exit(1)

    con = duckdb.connect(str(DB_PATH), read_only=True)
    suburbs = con.execute("SELECT * FROM suburbs").df()
    con.close()
    suburbs["card"] = suburbs.apply(_card, axis=1)
    print(f"Built {len(suburbs)} suburb cards", flush=True)

    cards = suburbs["card"].tolist()
    embeddings: list[list[float]] = []
    started = time.time()
    for i, card in enumerate(cards):
        attempt = 0
        while True:
            try:
                vec = embed.embed_batch([card])[0]
                embeddings.append(vec.tolist())
                break
            except Exception as exc:  # noqa: BLE001
                attempt += 1
                if attempt > 3:
                    raise
                wait = 2 ** attempt
                print(f"  card {i} failed ({exc}); retry {attempt} after {wait}s", flush=True)
                time.sleep(wait)
        if (i + 1) % 25 == 0 or i == len(cards) - 1:
            elapsed = time.time() - started
            print(f"  embedded {i + 1}/{len(cards)}  ({elapsed:.1f}s elapsed)", flush=True)

    out_df = suburbs[[
        "name", "region", "postcode", "family_friendliness", "safety",
        "public_transport", "affordability_buying", "median_house_price_2021",
        "time_to_cbd_pt_min", "card",
    ]].copy()
    out_df["embedding"] = embeddings
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_parquet(OUT_PATH, index=False)
    print(f"Wrote {len(out_df)} suburb embeddings ({len(embeddings[0])}-D) to {OUT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"build_review_embeddings failed: {exc}", file=sys.stderr)
        raise
