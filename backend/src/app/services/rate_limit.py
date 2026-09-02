"""In-process rate limiting for the anonymous, LLM-backed orb endpoints.

The demo runs as a single replica (Container Apps max_replicas = 1), so a
process-local sliding window is sufficient - no Redis, no extra dependency.
Two independent gates:

  per-IP     ORB_RATE_LIMIT_PER_IP requests per ORB_RATE_LIMIT_WINDOW_SECONDS
  global     ORB_RATE_LIMIT_GLOBAL requests per ORB_RATE_LIMIT_WINDOW_SECONDS

The global gate is the cost circuit-breaker: one orb call can fan out to
several LLM completions plus Tavily searches, so a burst from many
addresses is capped as a whole. Counters reset when the replica scales to
zero, which is acceptable for a demo - the goal is to make quota burn
uneconomic, not to be a billing system.

Client IP: the backend sits behind nginx (sidecar) and Container Apps'
Envoy ingress, both of which append to X-Forwarded-For. We take the
rightmost address that is not loopback/private, which is the address the
ingress recorded, so a client cannot spoof it by prepending entries.
"""

from __future__ import annotations

import ipaddress
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from src.app.services.auth import has_write_token
from src.settings import settings


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, now: float | None = None) -> bool:
        """Record a hit for `key`. Returns True if allowed, False if over limit."""
        if self.limit <= 0:
            return True
        now = time.monotonic() if now is None else now
        cutoff = now - self.window
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            # Drop empty buckets so the dict does not grow with every IP seen.
            if not hits:
                del self._hits[key]
            return True


def _is_private(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    # not is_global covers private, loopback, link-local, reserved and the
    # RFC 5737 documentation ranges.
    return not addr.is_global


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    for raw in reversed([p.strip() for p in forwarded.split(",") if p.strip()]):
        if not _is_private(raw):
            return raw
    return request.client.host if request.client else "unknown"


_per_ip = SlidingWindowLimiter(settings.orb_rate_limit_per_ip, settings.orb_rate_limit_window_seconds)
_global = SlidingWindowLimiter(settings.orb_rate_limit_global, settings.orb_rate_limit_window_seconds)


async def enforce_orb_rate_limit(request: Request) -> None:
    """FastAPI dependency. Raises 429 when either gate is exceeded.
    The operator (demo write token) is exempt so live demos are never
    throttled by other visitors' traffic."""
    if has_write_token(request):
        return
    if not _global.check("global"):
        raise HTTPException(
            status_code=429,
            detail="The demo has hit its request ceiling for now. Please try again later.",
            headers={"Retry-After": str(int(settings.orb_rate_limit_window_seconds))},
        )
    if not _per_ip.check(client_ip(request)):
        raise HTTPException(
            status_code=429,
            detail="Too many requests from this address. Please slow down.",
            headers={"Retry-After": str(int(settings.orb_rate_limit_window_seconds))},
        )
