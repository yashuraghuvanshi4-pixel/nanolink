"""Unit and integration tests for Nanolink Python Client SDK."""

import socket
import threading
import unittest
from http.server import ThreadingHTTPServer
from nanolink.client import NanolinkClient, NanolinkAPIError
from nanolink.server.handler import NanolinkRequestHandler
from nanolink.storage.db import Database


class TestClientSDK(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = Database(":memory:")
        # Bind to ephemeral port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        cls.port = sock.getsockname()[1]
        sock.close()

        handler_cls = type(
            "TestClientHandler",
            (NanolinkRequestHandler,),
            {"default_db": cls.db, "enable_logging": False},
        )
        cls.server = ThreadingHTTPServer(("127.0.0.1", cls.port), handler_cls)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.client = NanolinkClient(base_url=f"http://127.0.0.1:{cls.port}")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_health_check(self):
        res = self.client.health()
        self.assertEqual(res["status"], "ok")

    def test_shorten_and_get_stats(self):
        res = self.client.shorten("https://github.com", alias="sdk-gh", tags=["git", "code"])
        self.assertEqual(res["code"], "sdk-gh")
        self.assertEqual(res["target_url"], "https://github.com")

        # Get stats
        stats = self.client.get_stats("sdk-gh")
        self.assertEqual(stats["link"]["code"], "sdk-gh")
        self.assertEqual(stats["total_clicks"], 0)

    def test_bulk_shorten(self):
        items = [
            {"url": "https://example.com/one", "alias": "sdk-b1"},
            {"url": "https://example.com/two", "alias": "sdk-b2"},
        ]
        res = self.client.bulk_shorten(items)
        self.assertEqual(res["total"], 2)
        self.assertEqual(len(res["results"]), 2)

    def test_list_and_search(self):
        self.client.shorten("https://news.ycombinator.com", alias="sdk-hn", tags=["news"])
        links = self.client.list_links(limit=10)
        self.assertIn("links", links)
        self.assertGreaterEqual(len(links["links"]), 1)

        search_res = self.client.search("sdk-hn")
        self.assertIn("results", search_res)
        self.assertTrue(any(r["code"] == "sdk-hn" for r in search_res["results"]))

    def test_api_error_handling(self):
        with self.assertRaises(NanolinkAPIError) as ctx:
            # Invalid URL scheme
            self.client.shorten("ftp://invalid-url.com")
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
