import unittest
from nanolink.core.export import export_clicks_to_csv, export_stats_to_json
from nanolink.models import ClickEvent, Link, LinkStats


class TestExport(unittest.TestCase):
    def test_export_clicks_to_csv(self):
        clicks = [
            ClickEvent(
                id=1,
                link_code="code1",
                timestamp="2026-10-28T00:00:00Z",
                browser="Chrome",
                os="macOS",
                device_type="desktop",
                referer_domain="github.com",
                country="US",
            ),
            ClickEvent(
                id=2,
                link_code="code1",
                timestamp="2026-10-28T01:00:00Z",
                browser="Firefox",
                os="Linux",
                device_type="desktop",
                referer_domain="news.ycombinator.com",
                country="DE",
            ),
        ]
        csv_str = export_clicks_to_csv(clicks)
        lines = csv_str.strip().split("\n")
        self.assertEqual(len(lines), 3)  # header + 2 rows
        self.assertIn("link_code,timestamp,browser", lines[0])
        self.assertIn("code1,2026-10-28T00:00:00Z,Chrome", lines[1])

    def test_export_stats_to_json(self):
        link = Link(code="jcode", target_url="https://example.com")
        stats = LinkStats(link=link, total_clicks=5, unique_visitors=3)
        json_str = export_stats_to_json(stats)
        self.assertIn('"total_clicks": 5', json_str)
        self.assertIn('"unique_visitors": 3', json_str)


if __name__ == "__main__":
    unittest.main()
