"""In-process sliding-window rate limiter (SUG-05). Single instance only —
a documented limitation of the MVP deployment (TRD §8 item 5)."""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from .errors import AppError


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str) -> None:
        """Record one attempt; raise 429 RATE_LIMITED when over the limit."""
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] >= self.window:
                q.popleft()
            if len(q) >= self.limit:
                retry = int(self.window - (now - q[0])) + 1
                raise AppError("RATE_LIMITED", 429, "err.rate_limited",
                               extra={"retry_after_seconds": retry})
            q.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


# 30 auth requests / 10 min / IP (SUG-05)
auth_ip_limiter = SlidingWindowLimiter(limit=30, window_seconds=600)
