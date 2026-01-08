"""
API routes for newsletter subscription.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Form, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path

from app.db.database import get_db
from app.services import subscribers as subscribers_service
from app.services import email as email_service

router = APIRouter(prefix="/api", tags=["api"])

# Templates for responses
APP_DIR = Path(__file__).parent.parent
templates = Jinja2Templates(directory=APP_DIR / "templates")

# Simple in-memory rate limiting (resets on deploy)
# Format: {ip_address: [timestamp1, timestamp2, ...]}
rate_limit_store: dict[str, list[datetime]] = defaultdict(list)
RATE_LIMIT_MAX = 5  # Max subscriptions per IP
RATE_LIMIT_WINDOW = timedelta(hours=1)


def check_rate_limit(ip_address: str) -> bool:
    """
    Check if IP is rate limited.
    Returns True if request is allowed, False if rate limited.
    """
    now = datetime.utcnow()
    cutoff = now - RATE_LIMIT_WINDOW

    # Clean old entries
    rate_limit_store[ip_address] = [
        ts for ts in rate_limit_store[ip_address]
        if ts > cutoff
    ]

    # Check if over limit
    if len(rate_limit_store[ip_address]) >= RATE_LIMIT_MAX:
        return False

    # Record this request
    rate_limit_store[ip_address].append(now)
    return True


def get_client_ip(request: Request) -> str:
    """Get client IP from request, handling proxies."""
    # Check for forwarded header (common with proxies/load balancers)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Take the first IP in the chain
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/subscribe", response_class=HTMLResponse)
async def subscribe(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Handle newsletter subscription.
    Returns HTMX partial for in-place update.
    """
    ip_address = get_client_ip(request)

    # Rate limit check
    if not check_rate_limit(ip_address):
        return templates.TemplateResponse(
            "partials/subscribe_error.html",
            {
                "request": request,
                "error": "Too many requests. Please try again later."
            }
        )

    # Attempt subscription
    subscriber, status = subscribers_service.subscribe(
        db=db,
        email=email,
        ip_address=ip_address,
        source="website"
    )

    if status == "success":
        return templates.TemplateResponse(
            "partials/subscribe_success.html",
            {"request": request, "message": "Welcome! Check your inbox."}
        )
    elif status == "resubscribed":
        return templates.TemplateResponse(
            "partials/subscribe_success.html",
            {"request": request, "message": "Welcome back! You're resubscribed."}
        )
    elif status == "already_subscribed":
        return templates.TemplateResponse(
            "partials/subscribe_success.html",
            {"request": request, "message": "You're already subscribed!"}
        )
    elif status == "invalid_email":
        return templates.TemplateResponse(
            "partials/subscribe_error.html",
            {"request": request, "error": "Please enter a valid email address."}
        )
    else:
        return templates.TemplateResponse(
            "partials/subscribe_error.html",
            {"request": request, "error": "Something went wrong. Please try again."}
        )


@router.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe(
    request: Request,
    email: str = Query(...),
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Handle newsletter unsubscribe.
    Requires valid HMAC token to prevent abuse.
    """
    # Verify token
    if not email_service.verify_unsubscribe_token(email, token):
        return templates.TemplateResponse(
            "unsubscribe.html",
            {
                "request": request,
                "success": False,
                "error": "Invalid or expired unsubscribe link."
            }
        )

    # Process unsubscribe
    success, status = subscribers_service.unsubscribe(db, email)

    if success:
        return templates.TemplateResponse(
            "unsubscribe.html",
            {
                "request": request,
                "success": True,
                "message": "You've been unsubscribed from our newsletter."
            }
        )
    elif status == "not_found":
        return templates.TemplateResponse(
            "unsubscribe.html",
            {
                "request": request,
                "success": False,
                "error": "Email address not found in our list."
            }
        )
    else:
        return templates.TemplateResponse(
            "unsubscribe.html",
            {
                "request": request,
                "success": False,
                "error": "Something went wrong. Please try again."
            }
        )
