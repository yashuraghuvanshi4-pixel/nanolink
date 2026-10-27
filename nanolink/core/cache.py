"""Thread-safe in-memory LRU cache with TTL support for redirect resolution."""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple


class LRUCache:
    """Thread-safe Least Recently Used (LRU) cache with optional time-to-live (TTL)."""

    def __init__(self, maxsize: int = 10000, default_ttl: Optional[float] = None) -> None:
        self.maxsize = maxsize
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Tuple[Any, Optional[float]]] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Retrieve value by key. Returns None on cache miss or expiration."""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            val, expires_at = self._cache[key]
            if expires_at is not None and time.time() >= expires_at:
                # Expired entry
                del self._cache[key]
                self._misses += 1
                return None

            # Cache hit: promote to most recently used
            self._cache.move_to_end(key)
            self._hits += 1
            return val

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Store a key-value pair, evicting the least recently used item if needed."""
        ttl_seconds = ttl if ttl is not None else self.default_ttl
        expires_at = (time.time() + ttl_seconds) if ttl_seconds is not None else None

        with self._lock:
            if key in self._cache:
                del self._cache[key]
            elif len(self._cache) >= self.maxsize:
                # Evict oldest item (FIFO from front of OrderedDict)
                self._cache.popitem(last=False)

            self._cache[key] = (value, expires_at)

    def invalidate(self, key: str) -> bool:
        """Remove a key from cache. Returns True if key existed."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Remove all items from cache and reset counters."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> Dict[str, Any]:
        """Return cache telemetry and hit rate statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_ratio = (self._hits / total) if total > 0 else 0.0
            return {
                "size": len(self._cache),
                "maxsize": self.maxsize,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_ratio, 4),
            }
