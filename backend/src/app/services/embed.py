"""Provider-agnostic embedding helpers.

  embed_query(text)   -> np.ndarray (L2-normalised) | None on failure
  embed_batch(texts)  -> list[np.ndarray]

Both retrievers (regulations, reviews) and both build scripts go through
this module so the embedding model is configured in one place.

Provider is chosen by settings.embed_provider:
  "github"  -> GitHub Models text-embedding-3-small (1536-D)
  "bedrock" -> AWS Bedrock Titan v2 (1024-D; the original AWS path)

IMPORTANT: query vectors and corpus vectors must come from the SAME
model. Switching provider means rebuilding the RAG parquets with
scripts/build_regulation_corpus.py + scripts/build_review_embeddings.py
and setting settings.embed_dim to match.
"""

from __future__ import annotations

import logging
from typing import Iterable

import numpy as np

from src.settings import settings

log = logging.getLogger(__name__)


def _backend():
    if settings.embed_provider == "bedrock":
        from src.app.services import bedrock_embed
        return bedrock_embed
    from src.app.services import github_embed
    return github_embed


def embed_query(text: str) -> np.ndarray | None:
    """Embed one query string. Returns None on failure (callers degrade)."""
    try:
        return _backend().embed_query(text)
    except Exception as exc:  # noqa: BLE001
        log.warning("embed_query failed via %s (%s)", settings.embed_provider, exc)
        return None


def embed_batch(texts: Iterable[str]) -> list[np.ndarray]:
    """Embed a batch. Raises on failure (build scripts should fail loud)."""
    return _backend().embed_batch(texts)
