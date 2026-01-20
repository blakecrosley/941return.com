"""
Rate limiting middleware with bot classification.

Bot Tiers:
- TRUSTED: Search engines & AI crawlers - UNLIMITED access
- ALLOWED: SEO tools, social previews - Very high limits (1000/min)
- BLOCKED: Known attack tools - 403 Forbidden
- Everyone else: Regular anonymous limits (100/min)
"""

import logging
import re
import time
from collections import defaultdict
from functools import wraps
from typing import Callable, Optional

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# =============================================================================
# RATE LIMIT TIERS
# =============================================================================

RATE_LIMITS = {
    "anonymous": "30/minute",
    "authenticated": "1000/minute",
    "form": "10/minute",
    "auth": "20/minute",
    "trusted_bot": "unlimited",
    "allowed_bot": "1000/minute",
}

# =============================================================================
# BOT CLASSIFICATION
# =============================================================================

# TRUSTED BOTS - Unlimited access (we WANT these crawling)
TRUSTED_BOTS = {
    # Search engines
    "googlebot",
    "bingbot",
    "applebot",
    "applebot-extended",
    "duckduckbot",
    "yandexbot",
    "baiduspider",
    "slurp",
    "seznambot",
    "qwantify",
    # AI crawlers - Major companies
    "gptbot",
    "chatgpt-user",
    "oai-searchbot",
    "claudebot",
    "claude-web",
    "anthropic-ai",
    "perplexitybot",
    "google-extended",
    "gemini",
    "meta-externalagent",
    "meta-externalfetcher",
    "xai",
    "grok",
    # AI crawlers - Other players
    "ccbot",
    "bytespider",
    "cohere-ai",
    "amazonbot",
    "ai2bot",
    "diffbot",
    "youbot",
    "mistral",
    "deepmind",
    "huggingface",
    "ai21",
    "fireworksai",
    "togetherai",
    "inflection",
    "replicatebot",
    "runwayml",
    "stabilityai",
}

# ALLOWED BOTS - High limits (1000/min)
ALLOWED_BOTS = {
    # Social media link previews
    "facebookexternalhit",
    "facebookbot",
    "twitterbot",
    "linkedinbot",
    "discordbot",
    "slackbot",
    "telegrambot",
    "whatsapp",
    "pinterestbot",
    "redditbot",
    # SEO tools
    "ahrefsbot",
    "semrushbot",
    "mj12bot",
    "dotbot",
    "seranking",
    "dataforseobot",
    "serpstatbot",
    "rogerbot",
    "screaming frog",
    # Monitoring tools
    "uptimerobot",
    "pingdom",
    "gtmetrix",
    "lighthouse",
    "pagespeedonline",
    # Other legitimate
    "neevabot",
    "img2dataset",
}

# BLOCKED - Known attack tools (return 403 immediately)
BLOCKED_PATTERNS = [
    r"nikto",
    r"sqlmap",
    r"masscan",
    r"nmap",
    r"wp-scan",
    r"wpscan",
    r"havij",
    r"acunetix",
    r"nessus",
    r"openvas",
    r"burpsuite",
    r"dirbuster",
    r"gobuster",
    r"nuclei",
    r"zgrab",
]

# Parse rate limits
RATE_LIMIT_VALUES = {}
for key, value in RATE_LIMITS.items():
    if value == "unlimited":
        RATE_LIMIT_VALUES[key] = None
    else:
        RATE_LIMIT_VALUES[key] = int(value.split("/")[0])


def classify_bot(user_agent: str) -> Optional[str]:
    """Classify request based on user agent."""
    if not user_agent:
        return None  # Empty UA = anonymous user, gets normal limits

    ua_lower = user_agent.lower()

    # Check for blocked attack tools first
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, ua_lower):
            return "blocked"

    # Trusted bots - unlimited
    for bot in TRUSTED_BOTS:
        if bot in ua_lower:
            return "trusted_bot"

    # Allowed bots - high limits
    for bot in ALLOWED_BOTS:
        if bot in ua_lower:
            return "allowed_bot"

    # Everything else (curl, python-requests, browsers, etc.) = anonymous
    return None


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# =============================================================================
# IN-MEMORY RATE LIMITER
# =============================================================================

class InMemoryRateLimiter:
    """Sliding window rate limiter."""

    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = time.time()

    def _cleanup(self):
        now = time.time()
        if now - self._last_cleanup < 60:
            return
        cutoff = now - self.window_seconds
        for key in list(self._requests.keys()):
            self._requests[key] = [t for t in self._requests[key] if t > cutoff]
            if not self._requests[key]:
                del self._requests[key]
        self._last_cleanup = now

    def check(self, key: str, limit: int) -> tuple[bool, int, int]:
        """Check if allowed. Returns (allowed, remaining, reset_seconds)."""
        now = time.time()
        cutoff = now - self.window_seconds
        self._cleanup()

        self._requests[key] = [t for t in self._requests[key] if t > cutoff]
        current = len(self._requests[key])

        if current >= limit:
            oldest = min(self._requests[key]) if self._requests[key] else now
            reset = int(oldest + self.window_seconds - now) + 1
            return False, 0, reset

        self._requests[key].append(now)
        return True, limit - current - 1, self.window_seconds


_rate_limiter = InMemoryRateLimiter()


# =============================================================================
# MIDDLEWARE
# =============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with bot classification."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Skip for health checks and static files
        if path.startswith("/health") or path.startswith("/static"):
            return await call_next(request)

        user_agent = request.headers.get("user-agent", "")
        bot_type = classify_bot(user_agent)
        client_ip = get_client_ip(request)

        # BLOCKED: Known attack tools - reject immediately
        if bot_type == "blocked":
            logger.warning(
                f"Blocked attack tool: ip={client_ip} path={path} "
                f"user_agent={user_agent[:100]}"
            )
            return JSONResponse(
                status_code=403,
                content={"error": "Forbidden"},
            )

        # TRUSTED BOTS: Skip rate limiting entirely
        if bot_type == "trusted_bot":
            response = await call_next(request)
            response.headers["X-RateLimit-Category"] = "trusted_bot"
            return response

        # ALLOWED BOTS: High limits
        if bot_type == "allowed_bot":
            limit = RATE_LIMIT_VALUES["allowed_bot"]
            category = "allowed_bot"
        else:
            # Everyone else: anonymous limits
            limit = RATE_LIMIT_VALUES["anonymous"]
            category = "anonymous"

        # Check rate limit
        rate_key = f"{client_ip}:{category}"
        allowed, remaining, reset = _rate_limiter.check(rate_key, limit)

        if not allowed:
            logger.warning(
                f"Rate limit exceeded: ip={client_ip} category={category} "
                f"path={path} user_agent={user_agent[:100]}"
            )
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded"},
                headers={
                    "Retry-After": str(reset),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Category": category,
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Category"] = category
        return response


# =============================================================================
# DECORATORS
# =============================================================================

form_limiter = InMemoryRateLimiter()
auth_limiter = InMemoryRateLimiter()


def rate_limit_form(func: Callable) -> Callable:
    """Decorator for form endpoints."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request") or next(
            (arg for arg in args if isinstance(arg, Request)), None
        )
        if request:
            ip = get_client_ip(request)
            allowed, _, _ = form_limiter.check(ip, RATE_LIMIT_VALUES["form"])
            if not allowed:
                raise HTTPException(429, "Too many requests. Please try again later.")
        return await func(*args, **kwargs)
    return wrapper


def rate_limit_auth(func: Callable) -> Callable:
    """Decorator for auth endpoints."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request") or next(
            (arg for arg in args if isinstance(arg, Request)), None
        )
        if request:
            ip = get_client_ip(request)
            allowed, _, _ = auth_limiter.check(ip, RATE_LIMIT_VALUES["auth"])
            if not allowed:
                raise HTTPException(429, "Too many login attempts. Please try again later.")
        return await func(*args, **kwargs)
    return wrapper
