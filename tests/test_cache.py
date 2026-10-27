"""Unit tests for in-memory LRU redirect cache."""

import time
import unittest
from nanolink.core.cache import LRUCache
from nanolink.core.service import LinkService
from nanolink.storage.db import Database


class TestLRUCache(unittest.TestCase):
    def test_cache_set_and_get(self):
        cache = LRUCache(maxsize=3)
        cache.set("a", 1)
        cache.set("b", 2)
        self.assertEqual(cache.get("a"), 1)
        self.assertEqual(cache.get("b"), 2)
        self.assertIsNone(cache.get("c"))

    def test_lru_eviction_policy(self):
        cache = LRUCache(maxsize=2)
        cache.set("first", 10)
        cache.set("second", 20)

        # Access 'first' to make 'second' the least recently used
        _ = cache.get("first")

        # Insert third item, which should evict 'second'
        cache.set("third", 30)

        self.assertEqual(cache.get("first"), 10)
        self.assertIsNone(cache.get("second"))
        self.assertEqual(cache.get("third"), 30)

    def test_cache_ttl_expiration(self):
        cache = LRUCache(maxsize=10, default_ttl=0.05)
        cache.set("ephemeral", "value")
        self.assertEqual(cache.get("ephemeral"), "value")

        time.sleep(0.06)
        self.assertIsNone(cache.get("ephemeral"))

    def test_cache_stats(self):
        cache = LRUCache(maxsize=5)
        cache.set("k1", 100)
        _ = cache.get("k1")  # Hit
        _ = cache.get("k2")  # Miss
        stats = cache.stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["hit_rate"], 0.5)

    def test_link_service_cache_integration(self):
        db = Database(":memory:")
        service = LinkService(db, enable_cache=True, cache_size=100)

        link = service.shorten("https://fast-redirect.com", custom_alias="fast")
        self.assertIsNotNone(service.cache)

        # First resolve: cache miss (fetches from db and populates cache)
        r1 = service.resolve("fast")
        self.assertEqual(r1.code, "fast")
        self.assertEqual(service.cache.stats()["hits"], 0)
        self.assertEqual(service.cache.stats()["misses"], 1)

        # Second resolve: cache hit!
        r2 = service.resolve("fast")
        self.assertEqual(r2.code, "fast")
        self.assertEqual(service.cache.stats()["hits"], 1)

        # Deleting link invalidates cache
        service.delete("fast")
        self.assertIsNone(service.cache.get("fast"))


if __name__ == "__main__":
    unittest.main()
