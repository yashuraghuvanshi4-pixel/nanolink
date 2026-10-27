import unittest
from nanolink.core.analytics import (
    anonymize_ip,
    parse_user_agent,
    extract_referrer_domain,
    AnalyticsEngine,
)
from nanolink.storage.db import Database
from nanolink.models import Link


class TestAnalytics(unittest.TestCase):
    def test_anonymize_ip(self):
        h1 = anonymize_ip("192.168.1.50", "2026-10-27")
        h2 = anonymize_ip("192.168.1.50", "2026-10-27")
        h3 = anonymize_ip("192.168.1.50", "2026-10-28")
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)
        self.assertEqual(len(h1), 16)

    def test_parse_user_agent(self):
        # Chrome on macOS
        ua_chrome = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        browser, os_name, device = parse_user_agent(ua_chrome)
        self.assertEqual(browser, "Chrome")
        self.assertEqual(os_name, "macOS")
        self.assertEqual(device, "desktop")

        # iPhone Safari
        ua_iphone = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
        )
        browser, os_name, device = parse_user_agent(ua_iphone)
        self.assertEqual(browser, "Safari")
        self.assertEqual(os_name, "iOS")
        self.assertEqual(device, "mobile")

        # Curl / Bot
        ua_curl = "curl/8.4.0"
        browser, os_name, device = parse_user_agent(ua_curl)
        self.assertEqual(browser, "Bot/Curl")
        self.assertEqual(device, "bot")

    def test_extract_referrer_domain(self):
        self.assertEqual(
            extract_referrer_domain("https://www.twitter.com/post/123"), "twitter.com"
        )
        self.assertEqual(
            extract_referrer_domain("https://news.ycombinator.com/item?id=1"),
            "news.ycombinator.com",
        )
        self.assertIsNone(extract_referrer_domain(None))
        self.assertIsNone(extract_referrer_domain(""))

    def test_analytics_engine_recording_and_aggregation(self):
        db = Database(":memory:")
        db.save_link(Link(code="stats_test", target_url="https://example.com"))
        engine = AnalyticsEngine(db)

        engine.record_click(
            link_code="stats_test",
            ip="1.2.3.4",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0",
            referer="https://github.com/trending",
        )
        engine.record_click(
            link_code="stats_test",
            ip="1.2.3.4",  # same IP, same visitor
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0",
            referer="https://github.com/explore",
        )
        engine.record_click(
            link_code="stats_test",
            ip="5.6.7.8",  # different IP
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1",
            referer=None,
        )

        stats = engine.get_link_stats("stats_test")
        self.assertIsNotNone(stats)
        self.assertEqual(stats.total_clicks, 3)
        self.assertEqual(stats.unique_visitors, 2)
        self.assertEqual(stats.browsers.get("Chrome"), 2)
        self.assertEqual(stats.browsers.get("Safari"), 1)
        self.assertEqual(stats.devices.get("desktop"), 2)
        self.assertEqual(stats.devices.get("mobile"), 1)
        self.assertIn(("github.com", 2), stats.top_referrers)
        self.assertIn(("Direct / None", 1), stats.top_referrers)

    def test_resolve_country(self):
        from nanolink.core.analytics import resolve_country
        self.assertEqual(resolve_country({"CF-IPCountry": "US"}), "US")
        self.assertEqual(resolve_country({"CloudFront-Viewer-Country": "IN"}), "IN")
        self.assertEqual(resolve_country(ip="127.0.0.1"), "Local")
        self.assertEqual(resolve_country(ip="8.8.8.8"), "Unknown")


if __name__ == "__main__":
    unittest.main()
