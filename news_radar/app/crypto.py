"""Encrypts API keys at rest with Fernet.

The master key comes from NEWS_RADAR_SECRET, or is generated once into
data/.master.key (chmod 600). Losing that file means re-entering API keys.
"""
from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken

from .db import DATA_DIR

_KEY_FILE = DATA_DIR / ".master.key"


def _load_key() -> bytes:
    env = os.getenv("NEWS_RADAR_SECRET")
    if env:
        return env.encode()
    if _KEY_FILE.exists():
        return _KEY_FILE.read_bytes().strip()
    key = Fernet.generate_key()
    _KEY_FILE.write_bytes(key)
    try:
        os.chmod(_KEY_FILE, 0o600)
    except OSError:
        pass
    return key


_fernet = Fernet(_load_key())


def encrypt(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode() if value else ""


def decrypt(token: str) -> str:
    if not token:
        return ""
    try:
        return _fernet.decrypt(token.encode()).decode()
    except InvalidToken:
        return ""


def mask(value: str) -> str:
    if not value:
        return ""
    return "•" * 12 + value[-4:]
