"""
Admin routes for Return blog.
Protected by RETURN_ADMIN_ENABLED environment variable.
"""

import os
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pathlib import Path

from app.db.database import get_db
from app.services import posts as posts_service

router = APIRouter(prefix="/admin", tags=["admin"])

# Templates
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


def require_admin():
    """Dependency that checks if admin is enabled."""
    if os.getenv("RETURN_ADMIN_ENABLED", "").lower() != "true":
        raise HTTPException(status_code=404, detail="Not found")


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


@router.post("/posts/{post_id}/delete", dependencies=[Depends(require_admin)])
async def admin_delete_post(post_id: int, db: Session = Depends(get_db)):
    """Delete a post."""
    post = posts_service.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    posts_service.delete_post(db, post)
    return RedirectResponse("/admin/posts", status_code=303)
