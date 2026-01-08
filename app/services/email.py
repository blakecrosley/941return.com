"""
Email service using Resend API.
Handles contact creation, welcome emails, and unsubscribe.
"""

import os
import hmac
import hashlib
from typing import Optional
from urllib.parse import quote

import resend

# Initialize Resend with API key
resend.api_key = os.getenv("RESEND_API_KEY", "")

# Configuration
FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "hello@941return.com")
UNSUBSCRIBE_SECRET = os.getenv("UNSUBSCRIBE_SECRET", "change-me-in-production")
RESEND_AUDIENCE_ID = os.getenv("RESEND_AUDIENCE_ID", "9bb6a9a2-8103-45ee-8926-31af8f74a747")
BASE_URL = "https://941return.com"


def generate_unsubscribe_token(email: str) -> str:
    """Generate HMAC token for secure unsubscribe links."""
    return hmac.new(
        UNSUBSCRIBE_SECRET.encode(),
        email.lower().encode(),
        hashlib.sha256
    ).hexdigest()[:32]


def verify_unsubscribe_token(email: str, token: str) -> bool:
    """Verify an unsubscribe token is valid."""
    expected = generate_unsubscribe_token(email)
    return hmac.compare_digest(expected, token)


def get_unsubscribe_url(email: str) -> str:
    """Generate a secure unsubscribe URL."""
    token = generate_unsubscribe_token(email)
    encoded_email = quote(email, safe='')
    return f"{BASE_URL}/api/unsubscribe?email={encoded_email}&token={token}"


def create_contact(email: str) -> Optional[str]:
    """
    Create a contact in Resend.
    Returns the contact ID on success, None on failure.
    """
    if not resend.api_key:
        print("Warning: RESEND_API_KEY not set, skipping contact creation")
        return None

    try:
        result = resend.Contacts.create({
            "audience_id": RESEND_AUDIENCE_ID,
            "email": email,
            "unsubscribed": False,
        })
        return result.get("id")
    except Exception as e:
        print(f"Failed to create Resend contact: {e}")
        return None


def unsubscribe_contact(email: str) -> bool:
    """
    Mark a contact as unsubscribed in Resend.
    Returns True on success.
    """
    if not resend.api_key:
        print("Warning: RESEND_API_KEY not set, skipping unsubscribe")
        return True  # Return True so local unsubscribe still works

    try:
        # Update contact to unsubscribed
        resend.Contacts.update({
            "audience_id": RESEND_AUDIENCE_ID,
            "email": email,
            "unsubscribed": True,
        })
        return True
    except Exception as e:
        print(f"Failed to unsubscribe in Resend: {e}")
        return False


def send_welcome_email(email: str) -> bool:
    """
    Send welcome email to new subscriber.
    Returns True on success.
    """
    if not resend.api_key:
        print("Warning: RESEND_API_KEY not set, skipping welcome email")
        return False

    unsubscribe_url = get_unsubscribe_url(email)

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to Return</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0A0D12; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0A0D12; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="100%" max-width="500" cellpadding="0" cellspacing="0" style="max-width: 500px;">
                    <!-- Logo -->
                    <tr>
                        <td align="center" style="padding-bottom: 32px;">
                            <span style="font-family: Baskerville, Georgia, serif; font-size: 28px; color: #E8EDF3; letter-spacing: 0.02em;">Return<span style="color: #59B2CC;">...</span></span>
                        </td>
                    </tr>

                    <!-- Main content -->
                    <tr>
                        <td style="background-color: #12161D; border-radius: 12px; padding: 40px 32px;">
                            <h1 style="margin: 0 0 16px 0; font-family: Baskerville, Georgia, serif; font-size: 24px; font-weight: 400; color: #E8EDF3;">
                                Welcome to stillness.
                            </h1>
                            <p style="margin: 0 0 24px 0; font-size: 16px; line-height: 1.6; color: #9BA3AD;">
                                Thank you for subscribing. You'll receive occasional updates about Return—new features, meditation insights, and practice tips.
                            </p>
                            <p style="margin: 0 0 24px 0; font-size: 16px; line-height: 1.6; color: #9BA3AD;">
                                We respect your inbox. No spam, ever.
                            </p>
                            <p style="margin: 0; font-size: 16px; line-height: 1.6; color: #59B2CC;">
                                — The Return Team
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td align="center" style="padding-top: 32px;">
                            <p style="margin: 0; font-size: 12px; color: #5A6B7C;">
                                <a href="{unsubscribe_url}" style="color: #5A6B7C; text-decoration: underline;">Unsubscribe</a>
                                &nbsp;&nbsp;·&nbsp;&nbsp;
                                <a href="{BASE_URL}/privacy" style="color: #5A6B7C; text-decoration: underline;">Privacy</a>
                                &nbsp;&nbsp;·&nbsp;&nbsp;
                                <a href="{BASE_URL}/terms" style="color: #5A6B7C; text-decoration: underline;">Terms</a>
                            </p>
                            <p style="margin: 8px 0 0 0; font-size: 11px; color: #4A5568;">
                                &copy; 2025 941 Apps, LLC
                            </p>
                            <p style="margin: 4px 0 0 0; font-size: 11px; color: #3D4654;">
                                41 Wheeler Avenue, Unit 661807 · Arcadia, CA 91066 · USA
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

    text_content = f"""Welcome to Return...

Thank you for subscribing. You'll receive occasional updates about Return—new features, meditation insights, and practice tips.

We respect your inbox. No spam, ever.

— The Return Team

---
941 Apps, LLC
41 Wheeler Avenue, Unit 661807, Arcadia, CA 91066, USA

Unsubscribe: {unsubscribe_url}
Privacy: {BASE_URL}/privacy
Terms: {BASE_URL}/terms
"""

    try:
        resend.Emails.send({
            "from": f"Return <{FROM_EMAIL}>",
            "to": [email],
            "subject": "Welcome to Return...",
            "html": html_content,
            "text": text_content,
            # RFC 8058: List-Unsubscribe headers for one-click unsubscribe
            "headers": {
                "List-Unsubscribe": f"<{unsubscribe_url}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            },
        })
        return True
    except Exception as e:
        print(f"Failed to send welcome email: {e}")
        return False
