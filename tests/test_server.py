import json
import threading
import time
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from nanolink.server.handler import create_handler_factory
from nanolink.storage.db import Database


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = Database(":memory:")
        handler = create_handler_factory(cls.db)
        # Bind to port 0 to choose an open ephemeral port
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.port = cls.server.server_address[1]
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.05)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_health_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/health"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode())
            self.assertEqual(data["status"], "ok")

    def test_shorten_api_and_redirect(self):
        # 1. POST /api/shorten
        req_data = json.dumps({"url": "https://python.org", "alias": "py-srv"}).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/shorten",
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 201)
            data = json.loads(resp.read().decode())
            self.assertEqual(data["code"], "py-srv")

        # 2. GET /py-srv (Test 307 redirect without auto-following)
        class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None  # Prevent following redirect

        opener = urllib.request.build_opener(NoRedirectHandler)
        try:
            opener.open(f"http://127.0.0.1:{self.port}/py-srv")
        except urllib.error.HTTPError as err:
            self.assertEqual(err.code, 307)
            self.assertEqual(err.headers.get("Location"), "https://python.org")

        # 3. GET /api/stats/py-srv
        stats_url = f"http://127.0.0.1:{self.port}/api/stats/py-srv"
        with urllib.request.urlopen(stats_url) as resp:
            self.assertEqual(resp.status, 200)
            stats = json.loads(resp.read().decode())
            self.assertEqual(stats["total_clicks"], 1)

    def test_shorten_invalid_url_returns_400(self):
        req_data = json.dumps({"url": "not-valid"}).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/shorten",
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 400)

    def test_dashboard_ui_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/dashboard"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("text/html", resp.headers.get("Content-Type"))
            body = resp.read().decode("utf-8")
            self.assertIn("nanolink", body)
            self.assertIn("Shorten New URL", body)


if __name__ == "__main__":
    unittest.main()
