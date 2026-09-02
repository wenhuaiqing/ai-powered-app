"""GitHub Models embeddings (OpenAI-compatible, text-embedding-3-small).

Mirrors bedrock_embed's shape for the embed.py dispatcher. 1536-D by
default (set settings.embed_dim accordingly and REBUILD the RAG corpus
parquets when switching providers -- query and corpus vectors must come
from the same model).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Iterable

import numpy as np

from src.settings import settings

log = logging.getLogger(__name__)

_BATCH = 64  # keep request bodies modest for the free tier


@lru_cache(maxsize=1)
def _client():
    from openai import OpenAI
    return OpenAI(
        base_url=settings.github_models_base_url,
        api_key=settings.github_models_token,
    )


def _normalise(vec: list[float]) -> np.ndarray:
    arr = np.asarray(vec, dtype=np.float32)
    norm = np.linalg.norm(arr)
    return arr / norm if norm else arr


def embed_query(text: str) -> np.ndarray:
    """Embed one query string (L2-normalised)."""
    resp = _client().embeddings.create(
        model=settings.github_embed_model,
        input=[text],
    )
    return _normalise(resp.data[0].embedding)


def embed_batch(texts: Iterable[str]) -> list[np.ndarray]:
    """Embed a batch (build scripts). Raises on failure -- fail loud."""
    items = list(texts)
    out: list[np.ndarray] = []
    for i in range(0, len(items), _BATCH):
        chunk = items[i : i + _BATCH]
        resp = _client().embeddings.create(
            model=settings.github_embed_model,
            input=chunk,
        )
        # API preserves input order; sort by index defensively anyway.
        for d in sorted(resp.data, key=lambda d: d.index):
            out.append(_normalise(d.embedding))
        log.info("embedded %d/%d", min(i + _BATCH, len(items)), len(items))
    return out
