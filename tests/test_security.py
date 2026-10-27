import unittest
from nanolink.core.security import is_safe_url


class TestSecurity(unittest.TestCase):
    def test_safe_public_url(self):
        safe, reason = is_safe_url("https://github.com/yashuraghuvanshi4-pixel")
        self.assertTrue(safe)
        self.assertIsNone(reason)

    def test_blocks_dangerous_protocols(self):
        safe, reason = is_safe_url("javascript:alert(1)")
        self.assertFalse(safe)
        safe, reason = is_safe_url("file:///etc/passwd")
        self.assertFalse(safe)
        safe, reason = is_safe_url("ftp://server.com")
        self.assertFalse(safe)

    def test_blocks_metadata_ip(self):
        safe, reason = is_safe_url("http://169.254.169.254/latest/meta-data/")
        self.assertFalse(safe)
        self.assertIn("blocked", reason.lower())

    def test_localhost_policy(self):
        # By default when allow_localhost is False
        safe, reason = is_safe_url("http://localhost:8000", allow_localhost=False)
        self.assertFalse(safe)

        # When allow_localhost is True (for local testing)
        safe, reason = is_safe_url("http://localhost:8000", allow_localhost=True)
        self.assertTrue(safe)


if __name__ == "__main__":
    unittest.main()
