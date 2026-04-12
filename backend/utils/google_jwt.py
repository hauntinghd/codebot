from __future__ import annotations

import json
import time
import logging
from typing import Dict, Any

import requests
import jwt

logger = logging.getLogger("codebot")

_JWKS_CACHE: Dict[str, Any] = {"keys": [], "expires_at": 0}

def _refresh_jwks() -> None:
    global _JWKS_CACHE
    try:
        r = requests.get("https://www.googleapis.com/oauth2/v3/certs", timeout=10)
        r.raise_for_status()
        data = r.json()
        # Set cache for 1 hour
        _JWKS_CACHE = {"keys": data.get("keys", []), "expires_at": int(time.time()) + 3600}
    except Exception as e:
        logger.warning("Failed to refresh Google JWKS: %s", e)

def get_jwk_for_kid(kid: str) -> Dict[str, Any]:
    now = int(time.time())
    if _JWKS_CACHE.get("expires_at", 0) < now:
        _refresh_jwks()
    for key in _JWKS_CACHE.get("keys", []):
        if key.get("kid") == kid:
            return key
    raise ValueError("JWK not found for kid")

def verify_id_token(id_token: str, audience: str) -> Dict[str, Any]:
    """Verify Google id_token signature and claims (aud, iss, exp).

    Returns decoded payload on success, raises Exception on failure.
    """
    try:
        headers = jwt.get_unverified_header(id_token)
        kid = headers.get("kid")
        if not kid:
            raise ValueError("Missing kid in id_token header")
        jwk = get_jwk_for_kid(kid)
        # PyJWT RSAAlgorithm can build key from jwk json
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))

        # Do a normal decode but do not strictly require issuer here — some
        # Google tokens may present slightly different issuer strings.
        # We'll verify audience and signature, then validate issuer leniently.
        payload = jwt.decode(
            id_token,
            key=public_key,
            algorithms=["RS256"],
            audience=audience,
            options={"verify_iss": False},
        )

        iss = payload.get("iss") or ""
        # Accept common Google issuer variants or any issuer that endswith 'accounts.google.com'
        if not (iss == "https://accounts.google.com" or iss == "accounts.google.com" or iss.endswith("accounts.google.com")):
            raise ValueError(f"Invalid issuer: {iss}")

        return payload
    except Exception as e:
        logger.debug("id_token verification failed: %s", e)
        raise
