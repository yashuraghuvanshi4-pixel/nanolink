import unittest
from unittest.mock import patch, MagicMock
from nanolink.core.webhooks import WebhookDispatcher


class TestWebhooks(unittest.TestCase):
    def test_dispatch_empty_url_returns_false(self):
        dispatcher = WebhookDispatcher()
        self.assertFalse(dispatcher.dispatch("", "link.expired", {}))

    @patch("urllib.request.urlopen")
    def test_dispatch_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        dispatcher = WebhookDispatcher()
        success = dispatcher.dispatch(
            "https://hooks.example.com/alerts",
            "link.expired",
            {"code": "abc123"},
            async_dispatch=False,
        )
        self.assertTrue(success)
        mock_urlopen.assert_called_once()

    @patch("urllib.request.urlopen")
    def test_dispatch_retry_on_failure(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Connection refused")
        dispatcher = WebhookDispatcher(max_retries=1)
        success = dispatcher.dispatch(
            "https://hooks.example.com/fail",
            "link.expired",
            {},
            async_dispatch=False,
        )
        self.assertFalse(success)
        self.assertEqual(mock_urlopen.call_count, 2)


if __name__ == "__main__":
    unittest.main()
