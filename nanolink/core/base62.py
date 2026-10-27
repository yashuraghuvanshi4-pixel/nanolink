"""Base62 encoding and hash-based token generation.

Base62 uses characters [0-9a-zA-Z] (62 distinct characters).
A 7-character Base62 string provides 62^7 = 3.52 trillion unique combinations,
making it compact and URL-safe without requiring URL encoding.
"""

from __future__ import annotations

import hashlib
import secrets
from typing import Final

BASE62_ALPHABET: Final[str] = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE: Final[int] = len(BASE62_ALPHABET)


def encode(num: int) -> str:
    """Encode a non-negative integer into a Base62 string.

    Args:
        num: Non-negative integer to encode.

    Returns:
        Base62 encoded string representation.

    Raises:
        ValueError: If num is negative.
    """
    if num < 0:
        raise ValueError(f"Cannot encode negative integer: {num}")
    if num == 0:
        return BASE62_ALPHABET[0]

    digits = []
    n = num
    while n > 0:
        n, rem = divmod(n, BASE)
        digits.append(BASE62_ALPHABET[rem])

    return "".join(reversed(digits))


def decode(token: str) -> int:
    """Decode a Base62 string back into its original integer.

    Args:
        token: Base62 encoded string.

    Returns:
        The decoded integer value.

    Raises:
        ValueError: If token contains characters outside the Base62 alphabet.
    """
    if not token:
        raise ValueError("Cannot decode empty string")

    result = 0
    for char in token:
        idx = BASE62_ALPHABET.find(char)
        if idx == -1:
            raise ValueError(f"Invalid character '{char}' in Base62 token: {token}")
        result = result * BASE + idx

    return result


def generate_code_from_hash(url: str, length: int = 7, salt: str = "") -> str:
    """Generate a deterministic Base62 code by hashing the URL.

    Uses SHA-256 to hash (url + salt), extracts integer value, and encodes to Base62.
    If the resulting string is shorter than `length`, it is left-padded.
    If longer, the first `length` characters are returned.

    Args:
        url: Original target URL.
        length: Target length for the generated code (default 7).
        salt: Optional salt for collision resolution attempts.

    Returns:
        A deterministic Base62 string of specified length.
    """
    digest = hashlib.sha256(f"{url}:{salt}".encode("utf-8")).digest()
    # Use first 8 bytes (64-bit integer) to convert into Base62
    num = int.from_bytes(digest[:8], byteorder="big")
    code = encode(num)
    if len(code) >= length:
        return code[:length]
    return code.rjust(length, BASE62_ALPHABET[0])


def generate_random_code(length: int = 7) -> str:
    """Generate a cryptographically secure random Base62 code.

    Args:
        length: Length of the generated code (default 7).

    Returns:
        Random Base62 string.
    """
    return "".join(secrets.choice(BASE62_ALPHABET) for _ in range(length))
