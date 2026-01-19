"""
CSRF protection for FastAPI + HTMX forms.

Uses HMAC-signed tokens with timestamps to prevent cross-site request forgery.
Tokens are validated without server-side state (stateless tokens).
"""

import hmac
import hashlib
import os
import secrets
import time
from typing import Optional

# CSRF secret key - generate a strong random key if not set
CSRF_SECRET = os.getenv("CSRF_SECRET", secrets.token_hex(32))

# Token expiration times
CSRF_TOKEN_EXPIRY = 3600  # 1 hour for regular forms
CSRF_TOKEN_EXPIRY_STRICT = 300  # 5 minutes for admin/sensitive operations


def generate_csrf_token() -> str:
    """Generate a signed CSRF token with timestamp.

    Token format: timestamp:random:signature
    The signature is HMAC-SHA256 of timestamp:random using CSRF_SECRET.
    """
    timestamp = str(int(time.time()))
    random_value = secrets.token_hex(16)
    payload = f"{timestamp}:{random_value}"

    signature = hmac.new(
        CSRF_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    return f"{payload}:{signature}"


def validate_csrf_token(token: Optional[str]) -> bool:
    """Validate a CSRF token.

    Checks:
    1. Token format is correct
    2. Signature is valid
    3. Token has not expired

    Returns True if token is valid, False otherwise.
    """
    if not token:
        return False

    parts = token.split(":")
    if len(parts) != 3:
        return False

    timestamp, random_value, provided_signature = parts

    # Verify timestamp is numeric
    try:
        token_time = int(timestamp)
    except ValueError:
        return False

    # Check expiration
    current_time = int(time.time())
    if current_time - token_time > CSRF_TOKEN_EXPIRY:
        return False

    # Verify signature
    payload = f"{timestamp}:{random_value}"
    expected_signature = hmac.new(
        CSRF_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, provided_signature)


def validate_csrf_token_strict(token: Optional[str]) -> bool:
    """Validate a CSRF token with strict 5-minute expiry.

    For admin operations and other sensitive actions that require
    tighter replay protection.

    Same as validate_csrf_token but with CSRF_TOKEN_EXPIRY_STRICT.
    """
    if not token:
        return False

    parts = token.split(":")
    if len(parts) != 3:
        return False

    timestamp, random_value, provided_signature = parts

    try:
        token_time = int(timestamp)
    except ValueError:
        return False

    # Strict 5-minute expiration
    current_time = int(time.time())
    if current_time - token_time > CSRF_TOKEN_EXPIRY_STRICT:
        return False

    # Verify signature
    payload = f"{timestamp}:{random_value}"
    expected_signature = hmac.new(
        CSRF_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, provided_signature)
