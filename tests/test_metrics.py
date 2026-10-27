import unittest
from nanolink.server.metrics import MetricsCollector
from nanolink.storage.db import Database
from nanolink.models import Link


class TestMetrics(unittest.TestCase):
    def test_metrics_collector(self):
        db = Database(":memory:")
        db.save_link(Link(code="m1", target_url="https://site1.com"))

        collector = MetricsCollector()
        collector.record_request("GET", 200)
        collector.record_request("POST", 201)
        collector.record_redirect()

        output = collector.generate_prometheus_text(db)
        self.assertIn("nanolink_uptime_seconds", output)
        self.assertIn("nanolink_total_links 1", output)
        self.assertIn("nanolink_redirects_total 1", output)
        self.assertIn('nanolink_http_requests_total{method="GET",status="200"} 1', output)
        self.assertIn('nanolink_http_requests_total{method="POST",status="201"} 1', output)


if __name__ == "__main__":
    unittest.main()
