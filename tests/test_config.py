"""Unit tests for configuration and .env parser."""

import os
import tempfile
import unittest
from pathlib import Path
from nanolink.config import parse_dotenv, load_dotenv, Settings


class TestConfig(unittest.TestCase):
    def test_parse_dotenv(self):
        sample = """
        # Comments should be ignored
        NANOLINK_PORT=9090
        NANOLINK_HOST="0.0.0.0"
        EMPTY_VAL=
        SINGLE_QUOTES='hello world'
        INVALID_LINE_WITHOUT_EQUALS
        """
        parsed = parse_dotenv(sample)
        self.assertEqual(parsed["NANOLINK_PORT"], "9090")
        self.assertEqual(parsed["NANOLINK_HOST"], "0.0.0.0")
        self.assertEqual(parsed["SINGLE_QUOTES"], "hello world")
        self.assertEqual(parsed["EMPTY_VAL"], "")
        self.assertNotIn("INVALID_LINE_WITHOUT_EQUALS", parsed)

    def test_load_dotenv_from_file(self):
        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp:
            tmp.write("NANOLINK_TEST_FOO=bar123\n")
            tmp_path = tmp.name

        try:
            load_dotenv(tmp_path)
            self.assertEqual(os.environ.get("NANOLINK_TEST_FOO"), "bar123")
        finally:
            if "NANOLINK_TEST_FOO" in os.environ:
                del os.environ["NANOLINK_TEST_FOO"]
            Path(tmp_path).unlink(missing_ok=True)

    def test_settings_defaults(self):
        settings = Settings()
        self.assertEqual(settings.port, 8000)
        self.assertEqual(settings.host, "127.0.0.1")
        self.assertEqual(settings.db_path, "nanolink.db")
        self.assertFalse(settings.allow_localhost)

    def test_settings_from_env(self):
        os.environ["NANOLINK_PORT"] = "8080"
        os.environ["NANOLINK_ALLOW_LOCALHOST"] = "true"
        try:
            settings = Settings.from_env()
            self.assertEqual(settings.port, 8080)
            self.assertTrue(settings.allow_localhost)
        finally:
            del os.environ["NANOLINK_PORT"]
            del os.environ["NANOLINK_ALLOW_LOCALHOST"]


if __name__ == "__main__":
    unittest.main()
