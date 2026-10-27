"""Privacy-preserving analytics engine and lightweight user-agent parser."""

from __future__ import annotations

import hashlib
from collections import Counter
from datetime import datetime, timezone
from typing import Counter as CounterType, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from nanolink.models import ClickEvent, Link, LinkStats
from nanolink.storage.db import Database


def anonymize_ip(ip: str, salt_date: Optional[str] = None) -> str:
    """Hash client IP address with a daily salt for GDPR-compliant telemetry.

    Allows measuring daily unique visitors without storing identifiable IP addresses.
    """
    if not ip or ip.strip() == "":
        return "0000000000000000"
    date_component = salt_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return hashlib.sha256(f"{ip}:{date_component}:nanolink_salt".encode()).hexdigest()[:16]


def parse_user_agent(ua: Optional[str]) -> Tuple[str, str, str]:
    """Parse raw User-Agent header into (browser, os, device_type).

    Pure-Python parser with zero external dependencies.
    """
    if not ua or ua.strip() == "":
        return ("Unknown", "Unknown", "unknown")

    ua_lower = ua.lower()

    # Detect bot / crawler
    bots = ["bot", "crawler", "spider", "slurp", "facebookexternalhit", "curl", "wget"]
    if any(b in ua_lower for b in bots):
        browser = "Bot/Curl"
        os_name = "Unknown"
        device = "bot"
        return (browser, os_name, device)

    # Detect Device Type
    if "tablet" in ua_lower or "ipad" in ua_lower:
        device = "tablet"
    elif "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
        device = "mobile"
    else:
        device = "desktop"

    # Detect OS (check mobile OSes before desktop OSes because iOS UA contains 'like Mac OS X')
    if "iphone" in ua_lower or "ipad" in ua_lower or "ipod" in ua_lower:
        os_name = "iOS"
    elif "android" in ua_lower:
        os_name = "Android"
    elif "windows" in ua_lower:
        os_name = "Windows"
    elif "macintosh" in ua_lower or "mac os x" in ua_lower:
        os_name = "macOS"
    elif "linux" in ua_lower:
        os_name = "Linux"
    else:
        os_name = "Other"

    # Detect Browser (order matters: Edge contains Chrome/Safari, Chrome contains Safari)
    if "edg" in ua_lower:
        browser = "Edge"
    elif "opr" in ua_lower or "opera" in ua_lower:
        browser = "Opera"
    elif "firefox" in ua_lower:
        browser = "Firefox"
    elif "chrome" in ua_lower:
        browser = "Chrome"
    elif "safari" in ua_lower:
        browser = "Safari"
    else:
        browser = "Other"

    return (browser, os_name, device)


def extract_referrer_domain(referer: Optional[str]) -> Optional[str]:
    """Extract clean domain name from Referer header URL."""
    if not referer:
        return None
    try:
        parsed = urlparse(referer)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain if domain else None
    except Exception:
        return None


class AnalyticsEngine:
    """Manages click recording, IP anonymization, and aggregated statistics."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def record_click(
        self,
        link_code: str,
        ip: str,
        user_agent: Optional[str] = None,
        referer: Optional[str] = None,
    ) -> ClickEvent:
        """Record a redirect event and update link metrics."""
        browser, os_name, device = parse_user_agent(user_agent)
        referer_domain = extract_referrer_domain(referer)
        ip_hash = anonymize_ip(ip)

        event = ClickEvent(
            link_code=link_code,
            ip_hash=ip_hash,
            user_agent=user_agent,
            browser=browser,
            os=os_name,
            device_type=device,
            referer=referer,
            referer_domain=referer_domain,
        )

        self.db.record_click(event)
        self.db.increment_clicks(link_code)
        return event

    def get_link_stats(self, code: str) -> Optional[LinkStats]:
        """Aggregate all analytics data for a specific link."""
        link = self.db.get_link(code)
        if link is None:
            return None

        clicks = self.db.get_clicks_for_link(code)

        unique_ips = set()
        clicks_by_date: CounterType[str] = Counter()
        clicks_by_hour: CounterType[int] = Counter()
        referrers: CounterType[str] = Counter()
        browsers: CounterType[str] = Counter()
        os_counts: CounterType[str] = Counter()
        devices: CounterType[str] = Counter()

        for c in clicks:
            unique_ips.add(c.ip_hash)
            # Parse date and hour
            try:
                dt = datetime.fromisoformat(c.timestamp)
                date_key = dt.strftime("%Y-%m-%d")
                hour_key = dt.hour
                clicks_by_date[date_key] += 1
                clicks_by_hour[hour_key] += 1
            except ValueError:
                pass

            ref = c.referer_domain if c.referer_domain else "Direct / None"
            referrers[ref] += 1
            browsers[c.browser] += 1
            os_counts[c.os] += 1
            devices[c.device_type] += 1

        top_referrers = referrers.most_common(10)

        return LinkStats(
            link=link,
            total_clicks=len(clicks),
            unique_visitors=len(unique_ips),
            clicks_by_date=dict(sorted(clicks_by_date.items())),
            clicks_by_hour=dict(sorted(clicks_by_hour.items())),
            top_referrers=top_referrers,
            browsers=dict(browsers.most_common(5)),
            os_breakdown=dict(os_counts.most_common(5)),
            devices=dict(devices.most_common(5)),
        )
