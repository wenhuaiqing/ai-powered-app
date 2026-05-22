"""Cosine retrieval over the suburb-reviews embeddings parquet."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.app.services.ai_client import embed_model, get_openai_client
from src.settings import settings

log = logging.getLogger(__name__)


@dataclass
class SuburbHit:
    name: str
    region: str
    score: float
    median_house_price_2021: float | None
    family_friendliness: float | None
    safety: float | None
    public_transport: float | None
    affordability_buying: float | None
    time_to_cbd_pt_min: float | None
    card: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "region": self.region,
            "score": self.score,
            "median_house_price_2021": self.median_house_price_2021,
            "family_friendliness": self.family_friendliness,
            "safety": self.safety,
            "public_transport": self.public_transport,
            "affordability_buying": self.affordability_buying,
            "time_to_cbd_pt_min": self.time_to_cbd_pt_min,
            "card": self.card,
        }


@lru_cache(maxsize=1)
def _corpus() -> tuple[pd.DataFrame, np.ndarray] | None:
    path = Path(settings.data_dir) / "reviews_embeddings.parquet"
    if not path.exists():
        log.warning("Review embeddings not found at %s — reviews retrieval will return no hits", path)
        return None
    df = pd.read_parquet(path)
    matrix = np.array(df["embedding"].tolist(), dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    matrix = matrix / norms
    return df.drop(columns=["embedding"]), matrix


def _embed_query(query: str) -> np.ndarray | None:
    if not settings.azure_openai_api_key:
        return None
    try:
        client = get_openai_client()
        resp = client.embeddings.create(model=embed_model(), input=[query])
        vec = np.array(resp.data[0].embedding, dtype=np.float32)
        norm = np.linalg.norm(vec)
        return vec / norm if norm else vec
    except Exception as exc:  # noqa: BLE001
        log.warning("Query embedding failed (%s)", exc)
        return None


def _to_float(x: Any) -> float | None:
    try:
        if x is None:
            return None
        f = float(x)
        if f != f:  # NaN check
            return None
        return f
    except (TypeError, ValueError):
        return None


def retrieve(query: str, k: int = 4) -> list[SuburbHit]:
    corpus = _corpus()
    if corpus is None:
        return []
    df, matrix = corpus
    query_vec = _embed_query(query)
    if query_vec is None:
        return []

    scores = matrix @ query_vec
    top_idx = np.argsort(scores)[::-1][:k]
    hits: list[SuburbHit] = []
    for idx in top_idx:
        row = df.iloc[idx]
        hits.append(SuburbHit(
            name=str(row["name"]),
            region=str(row["region"]),
            score=float(scores[idx]),
            median_house_price_2021=_to_float(row.get("median_house_price_2021")),
            family_friendliness=_to_float(row.get("family_friendliness")),
            safety=_to_float(row.get("safety")),
            public_transport=_to_float(row.get("public_transport")),
            affordability_buying=_to_float(row.get("affordability_buying")),
            time_to_cbd_pt_min=_to_float(row.get("time_to_cbd_pt_min")),
            card=str(row["card"]),
        ))
    return hits
