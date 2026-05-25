"""AWS Bedrock Titan embeddings.

Single-vector queries via `invoke_model` against amazon.titan-embed-text-v2:0
(1024-D by default). Used by:
  - services/embed.embed_query     (RAG retrievers, per-query)
  - scripts/build_*_embeddings.py  (corpus build, batched)

Lazily constructs the boto3 client so this module imports cleanly in
unit tests without AWS creds.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Iterable

import numpy as np

from src.settings import settings

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _client():
    import boto3
    return boto3.client("bedrock-runtime", region_name=settings.aws_region)


def embed_query(text: str) -> np.ndarray:
    """Embed a single string via Titan. Returns L2-normalised numpy vector."""
    body = json.dumps({
        "inputText": text,
        "dimensions": settings.embed_dim,
        "normalize": True,  # Titan does the L2 norm server-side
    })
    response = _client().invoke_model(
        modelId=settings.bedrock_embed_model,
        body=body,
        contentType="application/json",
    )
    payload = json.loads(response["body"].read())
    return np.array(payload["embedding"], dtype=np.float32)


def embed_batch(texts: Iterable[str]) -> list[np.ndarray]:
    """Embed a sequence one-at-a-time (Titan invoke_model is single-input).

    For corpus builds. Caller batches its own iteration; we just keep
    the per-call shape consistent with the Azure batched embed.
    """
    return [embed_query(t) for t in texts]
