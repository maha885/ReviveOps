"""In-process limits that protect the free host (stdlib only).

* ``RateLimiter``: sliding-window limit per client key (IP). Memory is
  bounded: expired timestamps are pruned on access and the key table is
  capped; when full, stale keys are dropped first, then the least recently
  active ones.
* ``ConcurrencyLimiter``: NON-BLOCKING. When all slots are taken the request
  is rejected immediately (``TooManyConcurrent`` -> HTTP 429) instead of
  queueing, so a burst can't pile up waiting threads on a small instance.
  The slot is always released, including when the body raises.

Both are per-process and in-memory, which is enough for one free instance.
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from contextlib import contextmanager
from typing import Callable, Deque, Dict, Iterator, Optional

from app.config import settings


class RateLimited(Exception):
    """Too many requests from one client. ``retry_after`` is whole seconds >= 1."""

    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Try again in {retry_after}s.")


class TooManyConcurrent(Exception):
    """All concurrent slots are busy."""

    def __init__(self) -> None:
        super().__init__("Server is busy with other scans. Try again shortly.")


class RateLimiter:
    """Sliding-window limiter.

    ``max_per_minute`` may be an int or a zero-arg callable (read on every
    call, so settings changes/monkeypatching take effect). Values < 1 are
    treated as 1 so the limit can never be disabled by mistake.
    """

    def __init__(
        self,
        max_per_minute: "int | Callable[[], int]",
        window_seconds: float = 60,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = 10_000,
    ) -> None:
        self._max = max_per_minute
        self._window = window_seconds
        self._clock = clock
        self._max_keys = max(1, max_keys)
        self._hits: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def _limit(self) -> int:
        value = self._max() if callable(self._max) else self._max
        return max(1, int(value))

    def _prune(self, q: Deque[float], now: float) -> None:
        cutoff = now - self._window
        while q and q[0] <= cutoff:
            q.popleft()

    def _make_room(self, now: float) -> None:
        # Drop keys with no live timestamps first.
        for k in [k for k, q in self._hits.items() if not q or q[-1] <= now - self._window]:
            del self._hits[k]
        # Still full: evict least recently active keys.
        excess = len(self._hits) - self._max_keys + 1
        if excess > 0:
            oldest = sorted(self._hits, key=lambda k: self._hits[k][-1])[:excess]
            for k in oldest:
                del self._hits[k]

    def check(self, key: str) -> None:
        """Record a hit for ``key`` or raise ``RateLimited``."""
        limit = self._limit()
        with self._lock:
            now = self._clock()
            q = self._hits.get(key)
            if q is None:
                if len(self._hits) >= self._max_keys:
                    self._make_room(now)
                q = self._hits[key] = deque()
            else:
                self._prune(q, now)
            if len(q) >= limit:
                retry = math.ceil(q[0] + self._window - now)
                raise RateLimited(max(1, retry))
            q.append(now)

    def allow(self, key: str) -> bool:
        try:
            self.check(key)
        except RateLimited:
            return False
        return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def tracked_keys(self) -> int:
        with self._lock:
            return len(self._hits)


class ConcurrencyLimiter:
    """Non-blocking cap on simultaneous operations."""

    def __init__(self, max_concurrent: "int | Callable[[], int]") -> None:
        self._max = max_concurrent
        self._active = 0
        self._lock = threading.Lock()

    def _limit(self) -> int:
        value = self._max() if callable(self._max) else self._max
        return max(1, int(value))

    def try_acquire(self) -> bool:
        limit = self._limit()
        with self._lock:
            if self._active >= limit:
                return False
            self._active += 1
            return True

    def release(self) -> None:
        with self._lock:
            if self._active > 0:
                self._active -= 1

    @property
    def active(self) -> int:
        with self._lock:
            return self._active

    @contextmanager
    def slot(self) -> Iterator[None]:
        """Hold a slot for the ``with`` body; raise ``TooManyConcurrent`` if full."""
        if not self.try_acquire():
            raise TooManyConcurrent()
        try:
            yield
        finally:
            self.release()

    def __enter__(self) -> "ConcurrencyLimiter":
        if not self.try_acquire():
            raise TooManyConcurrent()
        return self

    def __exit__(self, *exc: object) -> None:
        self.release()


def client_key(request) -> str:
    """Client identifier for rate limiting: ``request.client.host``.

    X-Forwarded-For is deliberately NOT trusted (clients can spoof it to dodge
    or poison the limiter). Behind Render's proxy all clients may therefore
    appear as one IP; trusted-proxy handling is a future decision.
    """
    client = getattr(request, "client", None)
    host: Optional[str] = getattr(client, "host", None)
    return host or "unknown"


# Default instances read settings at call time. Call ``.reset()`` (rate) or
# replace/monkeypatch them in tests.
scan_rate_limiter = RateLimiter(lambda: settings.scan_rate_per_minute)
extraction_limiter = ConcurrencyLimiter(lambda: settings.max_concurrent_scans)
