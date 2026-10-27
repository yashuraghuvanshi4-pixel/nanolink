import io
import json
import unittest
from unittest.mock import patch
from nanolink.cli import main


class TestCLI(unittest.TestCase):
    def test_cli_shorten_and_resolve_json(self):
        # 1. Shorten
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = main(["--db", ":memory:", "shorten", "https://python.org", "--alias", "py-link", "--json"])
        self.assertEqual(code, 0)
        out = json.loads(buf.getvalue())
        self.assertEqual(out["code"], "py-link")
        self.assertEqual(out["target_url"], "https://python.org")

    def test_cli_stats_json_nonexistent(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = main(["--db", ":memory:", "stats", "not-a-code", "--json"])
        self.assertEqual(code, 1)
        out = json.loads(buf.getvalue())
        self.assertIn("error", out)

    def test_cli_list_empty(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = main(["--db", ":memory:", "list", "--json"])
        self.assertEqual(code, 0)
        out = json.loads(buf.getvalue())
        self.assertEqual(out, [])

    def test_cli_delete_forced(self):
        # With in-memory db, test delete flag
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = main(["--db", ":memory:", "delete", "testcode", "--force", "--json"])
        self.assertEqual(code, 1)  # failed because link didn't exist in memory DB
        out = json.loads(buf.getvalue())
        self.assertFalse(out["deleted"])


if __name__ == "__main__":
    unittest.main()
