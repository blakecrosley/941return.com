"""
Admin routes for Return blog.
Protected by session-based authentication with ADMIN_SECRET_TOKEN.
"""

import hashlib
import os
import secrets
from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException, Form, Cookie
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.services import posts as posts_service
from app.routes.pages import templates
from app.security.rate_limit import rate_limit_auth

router = APIRouter(prefix="/admin", tags=["admin"])

# Admin authentication settings
ADMIN_SECRET_TOKEN = os.getenv("ADMIN_SECRET_TOKEN")
ADMIN_SESSION_COOKIE = "admin_session"
ADMIN_COOKIE_MAX_AGE = 86400  # 24 hours
IS_PRODUCTION = os.getenv("RAILWAY_ENVIRONMENT") == "production"

# In-memory session store (valid for server lifetime)
_admin_sessions: set[str] = set()


def _generate_session_token() -> str:
    """Generate a secure session token."""
    return secrets.token_urlsafe(32)


def _hash_token(token: str) -> str:
    """Hash a token for secure comparison."""
    return hashlib.sha256(token.encode()).hexdigest()


def require_admin(request: Request, admin_session: Optional[str] = Cookie(None)):
    """Dependency that checks admin authentication.

    Requires:
    1. ADMIN_SECRET_TOKEN environment variable to be set
    2. Valid session cookie from successful login
    """
    # Admin feature must be enabled via env var
    if not ADMIN_SECRET_TOKEN:
        raise HTTPException(status_code=404, detail="Not found")

    # Check for valid session
    if not admin_session or _hash_token(admin_session) not in _admin_sessions:
        # Redirect to login page
        raise HTTPException(
            status_code=303,
            detail="Authentication required",
            headers={"Location": "/admin/login"}
        )


# =============================================================================
# AUTHENTICATION
# =============================================================================


@router.get("/login")
async def admin_login_page(request: Request):
    """Admin login page."""
    # If admin not configured, return 404
    if not ADMIN_SECRET_TOKEN:
        raise HTTPException(status_code=404, detail="Not found")

    return templates.TemplateResponse(
        "admin/login.html",
        {"request": request, "error": None}
    )


@router.post("/login")
@rate_limit_auth
async def admin_login(request: Request, token: str = Form(...)):
    """Process admin login."""
    if not ADMIN_SECRET_TOKEN:
        raise HTTPException(status_code=404, detail="Not found")

    # Constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(token, ADMIN_SECRET_TOKEN):
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Invalid token"},
            status_code=401
        )

    # Create session
    session_token = _generate_session_token()
    _admin_sessions.add(_hash_token(session_token))

    response = RedirectResponse("/admin/posts", status_code=303)
    response.set_cookie(
        key=ADMIN_SESSION_COOKIE,
        value=session_token,
        max_age=ADMIN_COOKIE_MAX_AGE,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax"
    )
    return response


@router.post("/logout")
async def admin_logout(admin_session: Optional[str] = Cookie(None)):
    """Admin logout."""
    # Invalidate session
    if admin_session:
        _admin_sessions.discard(_hash_token(admin_session))

    response = RedirectResponse("/admin/login", status_code=303)
    response.delete_cookie(
        key=ADMIN_SESSION_COOKIE,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax"
    )
    return response


# =============================================================================
# POST MANAGEMENT
# =============================================================================


@router.get("/posts", dependencies=[Depends(require_admin)])
async def admin_posts(request: Request, db: Session = Depends(get_db)):
    """List all posts for admin."""
    all_posts = posts_service.list_posts(db)
    return templates.TemplateResponse(
        "admin/posts.html",
        {"request": request, "posts": all_posts}
    )


@router.get("/posts/new", dependencies=[Depends(require_admin)])
async def admin_new_post(request: Request):
    """New post form."""
    return templates.TemplateResponse(
        "admin/edit.html",
        {"request": request, "post": None}
    )


@router.post("/posts/new", dependencies=[Depends(require_admin)])
async def admin_create_post(
    request: Request,
    title: str = Form(...),
    slug: str = Form(...),
    excerpt: str = Form(None),
    content_md: str = Form(...),
    featured_image: str = Form(None),
    seo_title: str = Form(None),
    seo_description: str = Form(None),
    db: Session = Depends(get_db)
):
    """Create a new post."""
    # Check for duplicate slug
    existing = posts_service.get_post_by_slug(db, slug)
    if existing:
        return templates.TemplateResponse(
            "admin/edit.html",
            {
                "request": request,
                "post": None,
                "error": f"A post with slug '{slug}' already exists"
            }
        )

    post = posts_service.create_post(
        db=db,
        title=title,
        slug=slug,
        content_md=content_md,
        excerpt=excerpt or None,
        featured_image=featured_image or None,
        seo_title=seo_title or None,
        seo_description=seo_description or None
    )

    return RedirectResponse(f"/admin/posts/{post.id}/edit", status_code=303)


@router.get("/posts/{post_id}/edit", dependencies=[Depends(require_admin)])
async def admin_edit_post(request: Request, post_id: int, db: Session = Depends(get_db)):
    """Edit post form."""
    post = posts_service.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return templates.TemplateResponse(
        "admin/edit.html",
        {"request": request, "post": post}
    )


@router.post("/posts/{post_id}/edit", dependencies=[Depends(require_admin)])
async def admin_update_post(
    request: Request,
    post_id: int,
    title: str = Form(...),
    slug: str = Form(...),
    excerpt: str = Form(None),
    content_md: str = Form(...),
    featured_image: str = Form(None),
    seo_title: str = Form(None),
    seo_description: str = Form(None),
    db: Session = Depends(get_db)
):
    """Update an existing post."""
    post = posts_service.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Check for slug conflict (different post with same slug)
    existing = posts_service.get_post_by_slug(db, slug)
    if existing and existing.id != post_id:
        return templates.TemplateResponse(
            "admin/edit.html",
            {
                "request": request,
                "post": post,
                "error": f"A post with slug '{slug}' already exists"
            }
        )

    posts_service.update_post(
        db=db,
        post=post,
        title=title,
        slug=slug,
        content_md=content_md,
        excerpt=excerpt or None,
        featured_image=featured_image or None,
        seo_title=seo_title or None,
        seo_description=seo_description or None
    )

    return templates.TemplateResponse(
        "admin/edit.html",
        {"request": request, "post": post, "success": "Post saved"}
    )


@router.post("/posts/{post_id}/publish", dependencies=[Depends(require_admin)])
async def admin_publish_post(post_id: int, db: Session = Depends(get_db)):
    """Publish a post."""
    post = posts_service.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    posts_service.publish_post(db, post)
    return RedirectResponse(f"/admin/posts/{post_id}/edit", status_code=303)


@router.post("/posts/{post_id}/unpublish", dependencies=[Depends(require_admin)])
async def admin_unpublish_post(post_id: int, db: Session = Depends(get_db)):
    """Unpublish a post."""
    post = posts_service.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    posts_service.unpublish_post(db, post)
    return RedirectResponse(f"/admin/posts/{post_id}/edit", status_code=303)


@router.post("/posts/{post_id}/schedule", dependencies=[Depends(require_admin)])
async def admin_schedule_post(
    post_id: int,
    scheduled_at: str = Form(...),
    db: Session = Depends(get_db)
):
    """Schedule a post for future publication."""
    post = posts_service.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Parse the datetime from the form
    schedule_datetime = datetime.fromisoformat(scheduled_at)
    posts_service.schedule_post(db, post, schedule_datetime)
    return RedirectResponse(f"/admin/posts/{post_id}/edit", status_code=303)


@router.post("/posts/{post_id}/delete", dependencies=[Depends(require_admin)])
async def admin_delete_post(post_id: int, db: Session = Depends(get_db)):
    """Delete a post."""
    post = posts_service.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    posts_service.delete_post(db, post)
    return RedirectResponse("/admin/posts", status_code=303)
