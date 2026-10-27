"""Unit tests for OpenAPI 3.0 specification and Swagger UI endpoint."""

import json
import socket
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from nanolink.server.handler import NanolinkRequestHandler
from nanolink.server.openapi import OPENAPI_SPEC, SWAGGER_UI_HTML
from nanolink.storage.db import Database


class TestOpenAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = Database(":memory:")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        cls.port = sock.getsockname()[1]
        sock.close()

        handler_cls = type(
            "TestOpenAPIHandler",
            (NanolinkRequestHandler,),
            {"default_db": cls.db, "enable_logging": False},
        )
        cls.server = ThreadingHTTPServer(("127.0.0.1", cls.port), handler_cls)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_spec_structure(self):
        self.assertEqual(OPENAPI_SPEC["openapi"], "3.0.3")
        self.assertEqual(OPENAPI_SPEC["info"]["title"], "Nanolink API")
        self.assertIn("/api/shorten", OPENAPI_SPEC["paths"])
        self.assertIn("/api/bulk-shorten", OPENAPI_SPEC["paths"])
        self.assertIn("/health", OPENAPI_SPEC["paths"])

    def test_openapi_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/openapi.json"
        with urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["openapi"], "3.0.3")

    def test_docs_swagger_ui_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/docs"
        with urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode("utf-8")
            self.assertIn("SwaggerUIBundle", html)
            self.assertIn("/openapi.json", html)


if __name__ == "__main__":
    unittest.main()
