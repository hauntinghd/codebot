"""BYOK (Bring Your Own Key) encryption/decryption."""
from __future__ import annotations

import base64
import logging
from typing import Optional

from fastapi import HTTPException

from backend.config import JWT_SECRET

logger = logging.getLogger("codebot")

# Import cryptography for BYOK encryption (only if available)
_crypto_available = False
_fernet_class = None
_hashes_module = None
_pbkdf2_class = None

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    _crypto_available = True
    _fernet_class = Fernet
    _hashes_module = hashes
    _pbkdf2_class = PBKDF2HMAC
except ImportError:
    logger.warning("cryptography library not available - BYOK feature will not work. Install with: pip install cryptography")

CRYPTOGRAPHY_AVAILABLE = _crypto_available


def _get_encryption_key() -> bytes:
    """Generate encryption key from JWT_SECRET using PBKDF2."""
    if not CRYPTOGRAPHY_AVAILABLE or _pbkdf2_class is None or _hashes_module is None:
        raise HTTPException(status_code=500, detail="Cryptography library not available")
    password = JWT_SECRET.encode("utf-8")
    salt = b"codebot_byok_salt_2026"
    kdf = _pbkdf2_class(
        algorithm=_hashes_module.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key for storage."""
    if not CRYPTOGRAPHY_AVAILABLE or _fernet_class is None:
        raise HTTPException(status_code=500, detail="Encryption not available. Please install cryptography library.")
    if not api_key:
        return ""
    fernet = _fernet_class(_get_encryption_key())
    encrypted = fernet.encrypt(api_key.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key from storage."""
    if not CRYPTOGRAPHY_AVAILABLE or _fernet_class is None:
        raise HTTPException(status_code=500, detail="Decryption not available. Please install cryptography library.")
    if not encrypted_key:
        return ""
    try:
        fernet = _fernet_class(_get_encryption_key())
        decrypted = fernet.decrypt(encrypted_key.encode("utf-8"))
        return decrypted.decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to decrypt API key: {e}")
        return ""


def validate_api_key_format(api_key: str, provider: str) -> bool:
    """Validate API key format for different providers."""
    if not api_key or len(api_key) < 10:
        return False

    provider = provider.lower()

    if provider == "openai":
        return api_key.startswith("sk-") and len(api_key) > 20
    elif provider == "anthropic":
        return api_key.startswith("sk-ant-") and len(api_key) > 30
    elif provider == "gemini":
        return 30 <= len(api_key) <= 50
    elif provider == "replicate":
        return api_key.startswith("r8_") and len(api_key) > 20
    elif provider in ("huggingface", "hf"):
        return len(api_key) >= 20
    elif provider == "grok":
        return len(api_key) >= 30

    return len(api_key) >= 20

