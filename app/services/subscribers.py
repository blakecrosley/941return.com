"""
Subscriber service for newsletter management.
Handles local database operations and syncs with Resend.
"""

import re
from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.db.models import Subscriber
from app.services import email as email_service


# Simple email regex (not perfect, but good enough)
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def is_valid_email(email: str) -> bool:
    """Check if email format is valid."""
    if not email or len(email) > 320:
        return False
    return bool(EMAIL_REGEX.match(email))


def get_subscriber(db: Session, email: str) -> Optional[Subscriber]:
    """Get subscriber by email (case-insensitive)."""
    return db.query(Subscriber).filter(
        Subscriber.email == email.lower()
    ).first()


def subscribe(
    db: Session,
    email: str,
    ip_address: Optional[str] = None,
    source: str = "website"
) -> Tuple[Optional[Subscriber], str]:
    """
    Subscribe an email to the newsletter.

    Returns (subscriber, message) tuple.
    - On success: (Subscriber, "success")
    - On already subscribed: (existing Subscriber, "already_subscribed")
    - On resubscribe: (Subscriber, "resubscribed")
    - On error: (None, error_message)
    """
    email = email.lower().strip()

    # Validate email format
    if not is_valid_email(email):
        return None, "invalid_email"

    # Check if already exists
    existing = get_subscriber(db, email)

    if existing:
        if existing.is_subscribed:
            return existing, "already_subscribed"
        else:
            # Resubscribe
            existing.unsubscribed_at = None
            existing.subscribed_at = datetime.utcnow()
            existing.ip_address = ip_address
            db.commit()
            db.refresh(existing)

            # Sync with Resend
            email_service.create_contact(email)

            # Send welcome email
            email_service.send_welcome_email(email)

            return existing, "resubscribed"

    # Create new subscriber
    try:
        # Create in Resend first
        resend_id = email_service.create_contact(email)

        # Create locally
        subscriber = Subscriber(
            email=email,
            resend_contact_id=resend_id,
            ip_address=ip_address,
            source=source,
        )
        db.add(subscriber)
        db.commit()
        db.refresh(subscriber)

        # Send welcome email
        email_service.send_welcome_email(email)

        return subscriber, "success"

    except Exception as e:
        db.rollback()
        print(f"Failed to create subscriber: {e}")
        return None, "error"


def unsubscribe(db: Session, email: str) -> Tuple[bool, str]:
    """
    Unsubscribe an email from the newsletter.

    Returns (success, message) tuple.
    """
    email = email.lower().strip()

    subscriber = get_subscriber(db, email)

    if not subscriber:
        return False, "not_found"

    if not subscriber.is_subscribed:
        return True, "already_unsubscribed"

    # Mark as unsubscribed
    subscriber.unsubscribed_at = datetime.utcnow()
    db.commit()

    # Sync with Resend
    email_service.unsubscribe_contact(email)

    return True, "success"


def list_subscribers(
    db: Session,
    include_unsubscribed: bool = False,
    limit: int = 100,
    offset: int = 0
) -> Tuple[list[Subscriber], int]:
    """
    List subscribers with pagination.
    Returns (subscribers, total_count) tuple.
    """
    query = db.query(Subscriber)

    if not include_unsubscribed:
        query = query.filter(Subscriber.unsubscribed_at.is_(None))

    total = query.count()

    subscribers = query.order_by(
        Subscriber.subscribed_at.desc()
    ).offset(offset).limit(limit).all()

    return subscribers, total


def get_subscriber_count(db: Session) -> int:
    """Get count of active subscribers."""
    return db.query(Subscriber).filter(
        Subscriber.unsubscribed_at.is_(None)
    ).count()
