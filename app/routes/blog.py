"""
Public blog routes for Return.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services import posts as posts_service
from app.routes.pages import templates

router = APIRouter(prefix="/blog", tags=["blog"])


POSTS_PER_PAGE = 12


@router.get("")
async def blog_index(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db)
):
    """Blog index - list published posts with pagination."""
    if page < 1:
        page = 1

    offset = (page - 1) * POSTS_PER_PAGE
    posts, total = posts_service.get_published_posts(db, limit=POSTS_PER_PAGE, offset=offset)

    total_pages = (total + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE

    return templates.TemplateResponse(
        "blog/list.html",
        {
            "request": request,
            "posts": posts,
            "page": page,
            "total_pages": total_pages,
            "total": total
        }
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
