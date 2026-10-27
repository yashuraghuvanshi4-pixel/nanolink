"""Environment configuration and zero-dependency .env parser."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


def parse_dotenv(content: str) -> Dict[str, str]:
    """Parse key-value pairs from .env formatted string."""
    env_vars: Dict[str, str] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        # Strip matching surrounding quotes
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        env_vars[key] = val
    return env_vars


def load_dotenv(filepath: Optional[str | Path] = None, override: bool = False) -> Dict[str, str]:
    """Load variables from a .env file into os.environ if file exists."""
    path = Path(filepath or ".env")
    if not path.is_file():
        return {}
    try:
        content = path.read_text(encoding="utf-8")
        parsed = parse_dotenv(content)
        for k, v in parsed.items():
            if override or k not in os.environ:
                os.environ[k] = v
        return parsed
    except OSError:
        return {}


@dataclass
class Settings:
    """Application settings resolved from environment variables."""

    host: str = "127.0.0.1"
    port: int = 8000
    db_path: str = "nanolink.db"
    base_url: str = "http://localhost:8000"
    rate_limit_per_minute: int = 100
    allow_localhost: bool = False

    @classmethod
    def from_env(cls, env_file: Optional[str | Path] = None) -> Settings:
        """Create Settings instance after loading .env if available."""
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        host = os.getenv("NANOLINK_HOST", "127.0.0.1")
        port = int(os.getenv("NANOLINK_PORT", "8000"))
        db_path = os.getenv("NANOLINK_DB_PATH", "nanolink.db")
        base_url = os.getenv("NANOLINK_BASE_URL", f"http://{host}:{port}")
        rate_limit = int(os.getenv("NANOLINK_RATE_LIMIT", "100"))
        allow_lh = os.getenv("NANOLINK_ALLOW_LOCALHOST", "0").lower() in ("1", "true", "yes")

        return cls(
            host=host,
            port=port,
            db_path=db_path,
            base_url=base_url,
            rate_limit_per_minute=rate_limit,
            allow_localhost=allow_lh,
        )
