"""nanolink - High-performance URL shortener & analytics engine."""

__version__ = "1.0.0"
__author__ = "Yashu Raghuvanshi"

from nanolink.client import NanolinkClient, NanolinkError, NanolinkAPIError

__all__ = ["__version__", "__author__", "NanolinkClient", "NanolinkError", "NanolinkAPIError"]
