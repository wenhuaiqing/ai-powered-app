"""Cosine retrieval over the regulation embeddings parquet.

Loads `data/regulations/embeddings.parquet` once per process. Embeds the
query via Bedrock Titan v2 (see services/embed.py).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from src.app.services.agents.schemas import Citation
from src.app.services.embed import embed_query as embed_query_via_bedrock
from src.settings import settings

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _corpus() -> tuple[pd.DataFrame, np.ndarray] | None:
    path = Path(settings.data_dir) / "regulations" / "embeddings.parquet"
    if not path.exists():
        log.warning("Regulation embeddings not found at %s — Compliance RAG will return no hits", path)
        return None
    df = pd.read_parquet(path)
    matrix = np.array(df["embedding"].tolist(), dtype=np.float32)
    # Normalise rows so cosine == dot product
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    matrix = matrix / norms
    return df.drop(columns=["embedding"]), matrix


def _embed_query(query: str) -> np.ndarray | None:
    vec = embed_query_via_bedrock(query)
    if vec is None:
        return None
    norm = np.linalg.norm(vec)
    return vec / norm if norm else vec


def retrieve(query: str, k: int = 4) -> list[Citation]:
    """Return the top-k most similar chunks as Citation objects."""
    corpus = _corpus()
    if corpus is None:
        return []
    df, matrix = corpus

    query_vec = _embed_query(query)
    if query_vec is None:
        return []

    scores = matrix @ query_vec
    top_idx = np.argsort(scores)[::-1][:k]
    out: list[Citation] = []
    for idx in top_idx:
        row = df.iloc[idx]
        out.append(Citation(
            source=row["source"],
            url=row["url"] or None,
            snippet=row["text"][:600],
            score=float(scores[idx]),
            source_type="local_corpus",
        ))
    return out
