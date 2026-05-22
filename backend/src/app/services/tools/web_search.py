"""Tavily web-search wrapper. Used by Market Watch and as a Compliance fallback.

Free tier on Tavily is 1000 searches/month, no card required. The wrapper
returns typed WebHit objects and degrades gracefully if no key is set.
"""

from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from typing import Any

from src.app.services.agents.schemas import WebHit
from src.settings import settings

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 12.0
DEFAULT_K = 5


@lru_cache(maxsize=1)
def _get_client():
    if not settings.tavily_api_key:
        return None
    try:
        from tavily import AsyncTavilyClient
    except ImportError as exc:  # noqa: BLE001
        log.warning("tavily-python not installed: %s", exc)
        return None
    return AsyncTavilyClient(api_key=settings.tavily_api_key)


def _to_hit(raw: dict[str, Any]) -> WebHit:
    return WebHit(
        title=str(raw.get("title") or raw.get("url") or "Untitled"),
        url=str(raw.get("url") or ""),
        snippet=str(raw.get("content") or raw.get("snippet") or "").strip(),
        score=float(raw.get("score") or 0.0),
        source_type="web",
    )


async def web_search(
    query: str,
    k: int = DEFAULT_K,
    include_domains: list[str] | None = None,
    search_depth: str = "advanced",
) -> list[WebHit]:
    """Run a Tavily search. Returns [] if no key is set or the call fails."""
    client = _get_client()
    if client is None:
        log.info("web_search skipped — TAVILY_API_KEY not configured")
        return []

    kwargs: dict[str, Any] = {
        "query": query,
        "max_results": max(1, min(k, 10)),
        "search_depth": search_depth,
    }
    if include_domains:
        kwargs["include_domains"] = include_domains

    try:
        response = await asyncio.wait_for(client.search(**kwargs), timeout=DEFAULT_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        log.warning("Tavily search timed out for %r", query)
        return []
    except Exception as exc:  # noqa: BLE001
        log.warning("Tavily search failed (%s) — returning empty results", exc)
        return []

    raw_results = response.get("results") or []
    return [_to_hit(r) for r in raw_results]
