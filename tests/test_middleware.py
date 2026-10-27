"""Unit tests for server middleware pipeline."""

import unittest
from unittest.mock import MagicMock
from nanolink.server.middleware import (
    BaseMiddleware,
    CORSMiddleware,
    TimingMiddleware,
    MiddlewarePipeline,
)


class TestMiddleware(unittest.TestCase):
    def test_cors_middleware_headers(self):
        cors = CORSMiddleware()
        mock_handler = MagicMock()
        headers = {}
        status, headers = cors.process_response(mock_handler, 200, headers)
        self.assertEqual(status, 200)
        self.assertEqual(headers["Access-Control-Allow-Origin"], "*")
        self.assertIn("GET", headers["Access-Control-Allow-Methods"])
        self.assertIn("Content-Type", headers["Access-Control-Allow-Headers"])

    def test_timing_middleware(self):
        timing = TimingMiddleware()
        mock_handler = MagicMock()
        timing.process_request(mock_handler)
        self.assertTrue(hasattr(mock_handler, "_request_start_time"))

        headers = {}
        status, headers = timing.process_response(mock_handler, 200, headers)
        self.assertIn("X-Response-Time", headers)
        self.assertTrue(headers["X-Response-Time"].endswith("ms"))

    def test_middleware_pipeline_execution(self):
        pipeline = MiddlewarePipeline()
        cors = CORSMiddleware(allow_origin="https://example.com")
        timing = TimingMiddleware()
        pipeline.add(cors)
        pipeline.add(timing)

        mock_handler = MagicMock()
        proceed = pipeline.execute_pre(mock_handler)
        self.assertTrue(proceed)

        status, headers = pipeline.execute_post(mock_handler, 200, {})
        self.assertEqual(headers["Access-Control-Allow-Origin"], "https://example.com")
        self.assertIn("X-Response-Time", headers)

    def test_pipeline_abort_pre(self):
        class AbortingMiddleware(BaseMiddleware):
            def process_request(self, handler):
                return False

        pipeline = MiddlewarePipeline([AbortingMiddleware()])
        mock_handler = MagicMock()
        proceed = pipeline.execute_pre(mock_handler)
        self.assertFalse(proceed)


if __name__ == "__main__":
    unittest.main()
