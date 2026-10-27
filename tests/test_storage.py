import unittest
import sqlite3
from nanolink.storage.db import Database
from nanolink.models import Link, ClickEvent


class TestStorage(unittest.TestCase):
    def setUp(self):
        # Use an in-memory database for unit testing
        self.db = Database(":memory:")

    def test_save_and_get_link(self):
        link = Link(
            code="test01",
            target_url="https://python.org",
            title="Python",
        )
        saved = self.db.save_link(link)
        self.assertIsNotNone(saved.id)

        fetched = self.db.get_link("test01")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.code, "test01")
        self.assertEqual(fetched.target_url, "https://python.org")
        self.assertEqual(fetched.title, "Python")

    def test_unique_code_constraint(self):
        link1 = Link(code="dup", target_url="https://site1.com")
        self.db.save_link(link1)

        link2 = Link(code="dup", target_url="https://site2.com")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.save_link(link2)

    def test_increment_clicks(self):
        link = Link(code="clicky", target_url="https://click.me")
        self.db.save_link(link)

        c1 = self.db.increment_clicks("clicky")
        self.assertEqual(c1, 1)
        c2 = self.db.increment_clicks("clicky")
        self.assertEqual(c2, 2)

        fetched = self.db.get_link("clicky")
        self.assertEqual(fetched.click_count, 2)

    def test_delete_link_cascades_clicks(self):
        link = Link(code="cascade1", target_url="https://example.com")
        self.db.save_link(link)

        event = ClickEvent(
            link_code="cascade1",
            ip_hash="hash123",
            browser="Firefox",
        )
        self.db.record_click(event)
        clicks_before = self.db.get_clicks_for_link("cascade1")
        self.assertEqual(len(clicks_before), 1)

        deleted = self.db.delete_link("cascade1")
        self.assertTrue(deleted)

        self.assertIsNone(self.db.get_link("cascade1"))
        clicks_after = self.db.get_clicks_for_link("cascade1")
        self.assertEqual(len(clicks_after), 0)

    def test_list_links_pagination(self):
        for i in range(5):
            self.db.save_link(Link(code=f"link_{i}", target_url=f"https://example.com/{i}"))

        links = self.db.list_links(limit=3, offset=0)
        self.assertEqual(len(links), 3)

        links_page2 = self.db.list_links(limit=3, offset=3)
        self.assertEqual(len(links_page2), 2)

    def test_global_metrics(self):
        self.db.save_link(Link(code="g1", target_url="https://1.com"))
        self.db.save_link(Link(code="g2", target_url="https://2.com"))
        self.db.record_click(ClickEvent(link_code="g1", ip_hash="h1"))
        self.db.record_click(ClickEvent(link_code="g1", ip_hash="h2"))

        metrics = self.db.get_global_metrics()
        self.assertEqual(metrics["total_links"], 2)
        self.assertEqual(metrics["total_clicks"], 2)


if __name__ == "__main__":
    unittest.main()
