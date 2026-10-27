import unittest
from datetime import datetime, timedelta, timezone
from nanolink.models import (
    Link,
    ClickEvent,
    LinkStats,
    validate_url,
    validate_alias,
)


class TestModels(unittest.TestCase):
    def test_validate_url(self):
        self.assertTrue(validate_url("https://example.com"))
        self.assertTrue(validate_url("http://localhost:8000/path?arg=1#hash"))
        self.assertTrue(validate_url("https://sub.domain.co.uk/test"))
        self.assertFalse(validate_url("javascript:alert(1)"))
        self.assertFalse(validate_url("ftp://example.com"))
        self.assertFalse(validate_url("not_a_url"))
        self.assertFalse(validate_url(""))

    def test_validate_alias(self):
        self.assertTrue(validate_alias("custom-link"))
        self.assertTrue(validate_alias("link_123"))
        self.assertTrue(validate_alias("abc"))
        self.assertFalse(validate_alias("ab"))  # too short
        self.assertFalse(validate_alias("has spaces"))
        self.assertFalse(validate_alias("slash/in/alias"))

    def test_link_expiration_by_clicks(self):
        link = Link(
            code="test12",
            target_url="https://example.com",
            max_clicks=5,
            click_count=4,
        )
        self.assertFalse(link.is_expired())
        link.click_count = 5
        self.assertTrue(link.is_expired())

    def test_link_expiration_by_time(self):
        now = datetime.now(timezone.utc)
        future = (now + timedelta(hours=1)).isoformat()
        past = (now - timedelta(hours=1)).isoformat()

        link_active = Link(
            code="active1",
            target_url="https://example.com",
            expires_at=future,
        )
        self.assertFalse(link_active.is_expired(now))

        link_expired = Link(
            code="expired1",
            target_url="https://example.com",
            expires_at=past,
        )
        self.assertTrue(link_expired.is_expired(now))

    def test_link_to_dict(self):
        link = Link(
            code="dict123",
            target_url="https://github.com",
            title="GitHub",
        )
        d = link.to_dict()
        self.assertEqual(d["code"], "dict123")
        self.assertEqual(d["target_url"], "https://github.com")
        self.assertFalse(d["is_expired"])

    def test_click_event_model(self):
        event = ClickEvent(
            link_code="dict123",
            ip_hash="abc123hash",
            browser="Chrome",
            os="macOS",
            device_type="desktop",
            referer_domain="twitter.com",
        )
        d = event.to_dict()
        self.assertEqual(d["link_code"], "dict123")
        self.assertEqual(d["browser"], "Chrome")
        self.assertEqual(d["device_type"], "desktop")


if __name__ == "__main__":
    unittest.main()
