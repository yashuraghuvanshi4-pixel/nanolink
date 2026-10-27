import time
import unittest
from nanolink.server.ratelimit import RateLimiter


class TestRateLimiter(unittest.TestCase):
    def test_rate_limiter_allows_under_limit(self):
        limiter = RateLimiter(max_requests=5, window_seconds=10)
        for _ in range(5):
            allowed, _ = limiter.is_allowed("127.0.0.1")
            self.assertTrue(allowed)

    def test_rate_limiter_blocks_over_limit(self):
        limiter = RateLimiter(max_requests=3, window_seconds=2)
        for _ in range(3):
            allowed, _ = limiter.is_allowed("1.2.3.4")
            self.assertTrue(allowed)

        # 4th request should be blocked
        allowed, retry_after = limiter.is_allowed("1.2.3.4")
        self.assertFalse(allowed)
        self.assertGreaterEqual(retry_after, 1)

    def test_rate_limiter_differentiates_clients(self):
        limiter = RateLimiter(max_requests=1, window_seconds=5)
        self.assertTrue(limiter.is_allowed("client_a")[0])
        self.assertFalse(limiter.is_allowed("client_a")[0])
        # client_b should still be allowed
        self.assertTrue(limiter.is_allowed("client_b")[0])


if __name__ == "__main__":
    unittest.main()
