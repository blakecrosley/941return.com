"""
Public blog routes for Return.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services import posts as posts_service
from app.routes.pages import templates

router = APIRouter(prefix="/blog", tags=["blog"])


@router.get("")
async def blog_index(request: Request, db: Session = Depends(get_db)):
    """Blog index - list published posts."""
    published_posts = posts_service.get_published_posts(db)
    return templates.TemplateResponse(
        "blog/list.html",
        {"request": request, "posts": published_posts}
    )


@router.get("/{slug}")
async def blog_post(request: Request, slug: str, db: Session = Depends(get_db)):
    """Single blog post view."""
    post = posts_service.get_post_by_slug(db, slug)

    if not post or post.status != 'published':
        raise HTTPException(status_code=404, detail="Post not found")

    return templates.TemplateResponse(
        "blog/post.html",
        {"request": request, "post": post}
    )
