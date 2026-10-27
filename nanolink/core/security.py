"""Security validation and SSRF/malicious domain protection."""

from __future__ import annotations

import ipaddress
import socket
from typing import Optional, Set, Tuple
from urllib.parse import urlparse

# Default blocklist of suspicious or loopback domains
DEFAULT_BLOCKED_HOSTS: Set[str] = {
    "169.254.169.254",  # AWS/GCP metadata service
    "metadata.google.internal",
    "instance-data",
}

DISALLOWED_SCHEMES: Set[str] = {
    "javascript", "file", "data", "ftp", "ssh", "telnet", "mailto"
}


def is_private_ip(hostname: str) -> bool:
    """Check whether a hostname or IP string resolves to a private or loopback IP."""
    try:
        ip = ipaddress.ip_address(hostname)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast
    except ValueError:
        pass

    # Try resolving hostname if it's not a direct IP
    try:
        ip_str = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except Exception:
        return False


def is_safe_url(url: str, allow_localhost: bool = False) -> Tuple[bool, Optional[str]]:
    """Validate destination URL against protocol abuse, SSRF, and blocked hosts.

    Returns:
        (is_safe: bool, reason: Optional[str])
    """
    if not url:
        return False, "URL cannot be empty."

    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False, "Malformed URL structure."

    scheme = parsed.scheme.lower()
    if scheme in DISALLOWED_SCHEMES or scheme not in ("http", "https"):
        return False, f"Unsupported or dangerous URL scheme: '{scheme}'."

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False, "URL is missing a valid hostname."

    if hostname in DEFAULT_BLOCKED_HOSTS:
        return False, f"Access to host '{hostname}' is blocked."

    if not allow_localhost:
        if hostname == "localhost" or hostname.endswith(".localhost"):
            return False, "Redirection to localhost is disabled for security."
        if is_private_ip(hostname):
            return False, f"Redirection to private/internal IP address '{hostname}' is blocked (SSRF Protection)."

    return True, None
