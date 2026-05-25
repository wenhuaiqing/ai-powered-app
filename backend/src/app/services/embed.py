"""Provider-agnostic embedding helpers. Bedrock Titan v2 by default.

  embed_query(text)   -> np.ndarray (L2-normalised)
  embed_batch(texts)  -> list[np.ndarray]

Both retrievers (regulations, reviews) and both build scripts go through
this module so the embedding model is configured in one place.

The dispatcher exists so an azure path can be wired back in trivially
if needed; today the only supported value is "bedrock".
"""

from __future__ import annotations

import logging
from typing import Iterable

import numpy as np

from src.app.services import bedrock_embed
from src.settings import settings

log = logging.getLogger(__name__)


def embed_query(text: str) -> np.ndarray | None:
    """Embed one query string. Returns None on failure (callers degrade)."""
    try:
        return bedrock_embed.embed_query(text)
    except Exception as exc:  # noqa: BLE001
        log.warning("Bedrock embed_query failed (%s)", exc)
        return None


def embed_batch(texts: Iterable[str]) -> list[np.ndarray]:
    """Embed a batch. Raises on failure (build scripts should fail loud)."""
    return bedrock_embed.embed_batch(texts)
