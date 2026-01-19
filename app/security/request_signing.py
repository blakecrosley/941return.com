"""
Request signing for sensitive operations.

Provides HMAC-signed request validation with:
- 5-minute timestamp window (replay protection)
- Request body integrity verification
- Constant-time signature comparison

Works alongside CSRF protection for defense in depth.

Usage:
    # In JavaScript (client-side):
    const signature = await signRequest('/api/admin/action', body);
    fetch(url, {
        headers: { 'X-Request-Signature': signature },
        body: JSON.stringify(body)
    });

    # In Python (server-side):
    @require_signed_request
    async def admin_action(request: Request):
        ...
"""

import hashlib
import hmac
import os
import secrets
import time
from functools import wraps
from typing import Callable, Optional

from fastapi import HTTPException, Request


# Signing secret - must be set in production
SIGNING_SECRET = os.getenv("REQUEST_SIGNING_SECRET", "")

# Fallback to CSRF secret if no separate signing secret
if not SIGNING_SECRET:
    SIGNING_SECRET = os.getenv("CSRF_SECRET", secrets.token_hex(32))

# Signature expiration (5 minutes)
SIGNATURE_EXPIRY_SECONDS = 300

# Header name for the signature
SIGNATURE_HEADER = "X-Request-Signature"


def generate_signature(
    method: str,
    path: str,
    timestamp: int,
    body: str = "",
) -> str:
    """Generate HMAC signature for a request.

    Signature covers:
    - HTTP method
    - Request path
    - Timestamp
    - Request body (for POST/PUT/PATCH)

    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path (e.g., /api/admin/action)
        timestamp: Unix timestamp
        body: Request body as string (empty for GET)

    Returns:
        Signature in format: timestamp:signature
    """
    # Create payload to sign
    body_hash = hashlib.sha256(body.encode()).hexdigest() if body else ""
    payload = f"{method}:{path}:{timestamp}:{body_hash}"

    signature = hmac.new(
        SIGNING_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    return f"{timestamp}:{signature}"


def validate_signature(
    signature: str,
    method: str,
    path: str,
    body: str = "",
) -> bool:
    """Validate a request signature.

    Checks:
    1. Signature format is correct
    2. Timestamp is within 5 minutes
    3. Signature matches expected value

    Args:
        signature: The signature header value (timestamp:signature)
        method: HTTP method
        path: Request path
        body: Request body

    Returns:
        True if valid, False otherwise
    """
    if not signature:
        return False

    parts = signature.split(":")
    if len(parts) != 2:
        return False

    try:
        timestamp = int(parts[0])
        provided_signature = parts[1]
    except (ValueError, IndexError):
        return False

    # Check timestamp is within window
    current_time = int(time.time())
    if abs(current_time - timestamp) > SIGNATURE_EXPIRY_SECONDS:
        return False

    # Generate expected signature
    body_hash = hashlib.sha256(body.encode()).hexdigest() if body else ""
    payload = f"{method}:{path}:{timestamp}:{body_hash}"

    expected_signature = hmac.new(
        SIGNING_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    # Constant-time comparison
    return hmac.compare_digest(expected_signature, provided_signature)


async def get_request_body(request: Request) -> str:
    """Get request body as string, handling async body reading."""
    try:
        body = await request.body()
        return body.decode("utf-8") if body else ""
    except Exception:
        return ""


def require_signed_request(func: Callable) -> Callable:
    """Decorator to require a valid request signature.

    For GET requests, only method/path/timestamp are signed.
    For POST/PUT/PATCH, the body is also included in the signature.

    Raises HTTPException(403) if signature is missing or invalid.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request") or next(
            (arg for arg in args if isinstance(arg, Request)), None
        )
        if not request:
            raise HTTPException(
                status_code=500,
                detail="Request object not found"
            )

        # Get signature from header
        signature = request.headers.get(SIGNATURE_HEADER)
        if not signature:
            raise HTTPException(
                status_code=403,
                detail="Missing request signature"
            )

        # Get body for non-GET requests
        body = ""
        if request.method in ("POST", "PUT", "PATCH"):
            body = await get_request_body(request)

        # Validate signature
        if not validate_signature(
            signature=signature,
            method=request.method,
            path=request.url.path,
            body=body,
        ):
            raise HTTPException(
                status_code=403,
                detail="Invalid or expired request signature"
            )

        return await func(*args, **kwargs)

    return wrapper


# JavaScript helper for client-side signing
SIGNING_JS = """
/**
 * Sign a request for sensitive operations.
 * Include the returned signature in the X-Request-Signature header.
 *
 * @param {string} method - HTTP method (GET, POST, etc.)
 * @param {string} path - Request path (e.g., /api/admin/action)
 * @param {string} body - Request body (empty for GET)
 * @param {string} secret - Signing secret (should match server)
 * @returns {Promise<string>} Signature in format timestamp:signature
 */
async function signRequest(method, path, body = '', secret) {
    const timestamp = Math.floor(Date.now() / 1000);
    const bodyHash = body ? await sha256(body) : '';
    const payload = `${method}:${path}:${timestamp}:${bodyHash}`;

    const signature = await hmacSha256(secret, payload);
    return `${timestamp}:${signature}`;
}

async function sha256(message) {
    const msgBuffer = new TextEncoder().encode(message);
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

async function hmacSha256(key, message) {
    const encoder = new TextEncoder();
    const keyData = encoder.encode(key);
    const msgData = encoder.encode(message);

    const cryptoKey = await crypto.subtle.importKey(
        'raw', keyData, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
    );

    const signature = await crypto.subtle.sign('HMAC', cryptoKey, msgData);
    const signatureArray = Array.from(new Uint8Array(signature));
    return signatureArray.map(b => b.toString(16).padStart(2, '0')).join('');
}
"""
