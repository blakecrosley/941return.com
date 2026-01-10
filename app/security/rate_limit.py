"""
Simple in-memory rate limiting for FastAPI endpoints.

Uses a sliding window counter approach with automatic cleanup.
Suitable for single-instance deployments.
"""

import time
from collections import defaultdict
from functools import wraps
from typing import Callable

from fastapi import HTTPException, Request


class RateLimiter:
    """In-memory rate limiter using sliding window counters."""

    def __init__(self, requests_per_minute: int = 10, cleanup_interval: int = 60):
        self.requests_per_minute = requests_per_minute
        self.cleanup_interval = cleanup_interval
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.last_cleanup = time.time()

    def _cleanup(self):
        """Remove expired entries to prevent memory growth."""
        current_time = time.time()
        if current_time - self.last_cleanup < self.cleanup_interval:
            return

        cutoff = current_time - 60
        keys_to_delete = []

        for key, timestamps in self.requests.items():
            # Remove old timestamps
            self.requests[key] = [t for t in timestamps if t > cutoff]
            if not self.requests[key]:
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del self.requests[key]

        self.last_cleanup = current_time

    def is_rate_limited(self, key: str) -> bool:
        """Check if a key is rate limited.

        Args:
            key: Unique identifier (usually IP address)

        Returns:
            True if rate limited, False otherwise
        """
        self._cleanup()
        current_time = time.time()
        cutoff = current_time - 60

        # Filter to only recent requests
        recent_requests = [t for t in self.requests[key] if t > cutoff]
        self.requests[key] = recent_requests

        if len(recent_requests) >= self.requests_per_minute:
            return True

        # Record this request
        self.requests[key].append(current_time)
        return False


# Global rate limiter instances for different endpoint types
form_limiter = RateLimiter(requests_per_minute=5)  # 5 form submissions per minute
auth_limiter = RateLimiter(requests_per_minute=10)  # 10 auth attempts per minute


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    # Check for forwarded IP (behind reverse proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP (original client)
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit_form(func: Callable) -> Callable:
    """Decorator to rate limit form submission endpoints."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request") or next(
            (arg for arg in args if isinstance(arg, Request)), None
        )
        if request and form_limiter.is_rate_limited(get_client_ip(request)):
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later."
            )
        return await func(*args, **kwargs)
    return wrapper


def rate_limit_auth(func: Callable) -> Callable:
    """Decorator to rate limit authentication endpoints."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request") or next(
            (arg for arg in args if isinstance(arg, Request)), None
        )
        if request and auth_limiter.is_rate_limited(get_client_ip(request)):
            raise HTTPException(
                status_code=429,
                detail="Too many login attempts. Please try again later."
            )
        return await func(*args, **kwargs)
    return wrapper
