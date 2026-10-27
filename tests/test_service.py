import unittest
from datetime import datetime, timedelta, timezone
from nanolink.core.service import (
    LinkService,
    InvalidURLError,
    InvalidAliasError,
    AliasAlreadyExistsError,
    LinkNotFoundError,
    LinkExpiredError,
)
from nanolink.storage.db import Database


class TestLinkService(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.service = LinkService(self.db)

    def test_shorten_valid_url(self):
        link = self.service.shorten("https://google.com")
        self.assertIsNotNone(link.code)
        self.assertEqual(len(link.code), 7)
        self.assertEqual(link.target_url, "https://google.com")

    def test_shorten_invalid_url_raises(self):
        with self.assertRaises(InvalidURLError):
            self.service.shorten("not-a-valid-url")

    def test_shorten_custom_alias(self):
        link = self.service.shorten("https://github.com", custom_alias="my-gh")
        self.assertEqual(link.code, "my-gh")

    def test_shorten_reserved_alias_raises(self):
        with self.assertRaises(InvalidAliasError):
            self.service.shorten("https://github.com", custom_alias="api")
        with self.assertRaises(InvalidAliasError):
            self.service.shorten("https://github.com", custom_alias="health")

    def test_shorten_duplicate_alias_raises(self):
        self.service.shorten("https://site1.com", custom_alias="taken")
        with self.assertRaises(AliasAlreadyExistsError):
            self.service.shorten("https://site2.com", custom_alias="taken")

    def test_resolve_success(self):
        saved = self.service.shorten("https://python.org", custom_alias="py-official")
        resolved = self.service.resolve("py-official")
        self.assertEqual(resolved.code, saved.code)
        self.assertEqual(resolved.target_url, "https://python.org")

    def test_resolve_nonexistent_raises(self):
        with self.assertRaises(LinkNotFoundError):
            self.service.resolve("doesnotexist")

    def test_resolve_expired_by_time_raises(self):
        # Create expired link
        past = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        link = self.service.shorten("https://expired.org", custom_alias="expired-time")
        # Manually alter expires_at in DB
        with self.db.get_connection() as conn:
            conn.execute("UPDATE links SET expires_at = ? WHERE code = ?", (past, "expired-time"))
            conn.commit()

        with self.assertRaises(LinkExpiredError):
            self.service.resolve("expired-time")

    def test_resolve_expired_by_clicks_raises(self):
        self.service.shorten("https://limited.org", custom_alias="capped", max_clicks=2)
        self.db.increment_clicks("capped")
        self.db.increment_clicks("capped")

        with self.assertRaises(LinkExpiredError):
            self.service.resolve("capped")

    def test_delete_link(self):
        self.service.shorten("https://todelete.org", custom_alias="temp")
        self.assertTrue(self.service.delete("temp"))
        with self.assertRaises(LinkNotFoundError):
            self.service.resolve("temp")


if __name__ == "__main__":
    unittest.main()
