"""
Symmetric encryption for sensitive AISettings fields (the per-workspace API key).

Uses Fernet (AES-128-CBC + HMAC). The key comes from ``AI["FIELD_ENCRYPTION_KEY"]``
when set; otherwise it is derived deterministically from ``SECRET_KEY`` so the
feature works out-of-the-box in development. In production, set a dedicated
``AI_FIELD_ENCRYPTION_KEY`` so rotating SECRET_KEY doesn't invalidate stored keys.
"""

from __future__ import annotations

import base64
import hashlib

from django.conf import settings


def _fernet():
    from cryptography.fernet import Fernet

    configured = settings.AI.get("FIELD_ENCRYPTION_KEY")
    if configured:
        key = configured.encode() if isinstance(configured, str) else configured
    else:
        # Derive a valid 32-byte urlsafe-base64 Fernet key from SECRET_KEY.
        digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    if not plaintext:
        return ""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except Exception:  # noqa: BLE001 — corrupt/rotated key -> treat as no key
        return ""
