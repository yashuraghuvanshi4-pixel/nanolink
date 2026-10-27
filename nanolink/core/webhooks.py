"""Webhook notification dispatcher for link lifecycle events."""

from __future__ import annotations

import json
import threading
import time
import urllib.request
from typing import Any, Dict, Optional
from nanolink.models import utc_now_iso


class WebhookDispatcher:
    """Dispatches asynchronous HTTP webhooks with retries."""

    def __init__(self, timeout: float = 3.0, max_retries: int = 2) -> None:
        self.timeout = timeout
        self.max_retries = max_retries

    def dispatch(
        self,
        webhook_url: str,
        event_name: str,
        payload: Dict[str, Any],
        async_dispatch: bool = True,
    ) -> bool:
        """Send webhook notification to destination URL."""
        if not webhook_url:
            return False

        envelope = {
            "event": event_name,
            "timestamp": utc_now_iso(),
            "data": payload,
        }

        if async_dispatch:
            thread = threading.Thread(
                target=self._send_with_retry,
                args=(webhook_url, envelope),
                daemon=True,
            )
            thread.start()
            return True
        else:
            return self._send_with_retry(webhook_url, envelope)

    def _send_with_retry(self, webhook_url: str, envelope: Dict[str, Any]) -> bool:
        body = json.dumps(envelope).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "nanolink-webhook/1.0",
            },
            method="POST",
        )

        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    if 200 <= resp.status < 300:
                        return True
            except Exception:
                if attempt < self.max_retries:
                    time.sleep(0.1 * (2 ** attempt))
        return False
