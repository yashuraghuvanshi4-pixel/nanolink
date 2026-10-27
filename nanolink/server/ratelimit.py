"""Thread-safe sliding window rate limiter for API endpoints."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Dict, List, Tuple


class RateLimiter:
    """Sliding-window log rate limiter with thread-safe lock."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._records: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self._last_cleanup = time.time()

    def is_allowed(self, client_id: str) -> Tuple[bool, int]:
        """Check whether request from client_id is permitted under rate limits.

        Returns:
            Tuple of (is_allowed: bool, retry_after: int)
        """
        now = time.time()
        window_start = now - self.window_seconds

        with self._lock:
            # Periodic cleanup every 5 minutes
            if now - self._last_cleanup > 300:
                self._cleanup(window_start)
                self._last_cleanup = now

            timestamps = self._records[client_id]
            # Prune timestamps older than window
            valid_timestamps = [ts for ts in timestamps if ts > window_start]
            self._records[client_id] = valid_timestamps

            if len(valid_timestamps) >= self.max_requests:
                earliest = valid_timestamps[0]
                retry_after = max(1, int(self.window_seconds - (now - earliest)))
                return False, retry_after

            valid_timestamps.append(now)
            return True, 0

    def _cleanup(self, window_start: float) -> None:
        """Purge stale client records to prevent memory leak."""
        stale_keys = [
            k for k, timestamps in self._records.items()
            if not timestamps or timestamps[-1] <= window_start
        ]
        for k in stale_keys:
            del self._records[k]
