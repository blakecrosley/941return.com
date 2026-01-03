from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime
import os

from app.db.database import get_db
from app.services import posts as posts_service

router = APIRouter()

# Set up templates
APP_DIR = Path(__file__).parent.parent
templates = Jinja2Templates(directory=APP_DIR / "templates")

# Cache bust using CSS file modification time (works in containers)
css_file = APP_DIR / "static" / "css" / "custom.css"
CACHE_BUST = str(int(os.path.getmtime(css_file))) if css_file.exists() else "1"

# Make cache_bust available in all templates
templates.env.globals["cache_bust"] = CACHE_BUST


@router.get("/")
async def home(request: Request, db: Session = Depends(get_db)):
    # Get 3 recent posts for homepage
    recent_posts, _ = posts_service.get_published_posts(db, limit=3, offset=0)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "recent_posts": recent_posts}
    )


@router.get("/privacy")
async def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})


@router.get("/terms")
async def terms(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})


@router.get("/support")
async def support(request: Request):
    return templates.TemplateResponse("support.html", {"request": request})


@router.get("/robots.txt")
async def robots():
    """Serve robots.txt at root level for search engines."""
    content = """User-agent: *
Allow: /

Sitemap: https://941return.com/sitemap.xml
"""
    return Response(content=content, media_type="text/plain")


@router.get("/sitemap.xml")
async def sitemap(db: Session = Depends(get_db)):
    """Generate dynamic sitemap including blog posts."""
    base_url = "https://941return.com"

    # Static pages
    static_pages = [
        {"loc": "/", "priority": "1.0"},
        {"loc": "/blog", "priority": "0.9"},
        {"loc": "/privacy", "priority": "0.5"},
        {"loc": "/terms", "priority": "0.5"},
        {"loc": "/support", "priority": "0.8"},
    ]

    # Get all published blog posts (already sorted by published_at DESC)
    posts, _ = posts_service.get_published_posts(db, limit=1000, offset=0)

    # Build XML
    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_parts.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    # Add static pages
    for page in static_pages:
        xml_parts.append("  <url>")
        xml_parts.append(f"    <loc>{base_url}{page['loc']}</loc>")
        xml_parts.append(f"    <priority>{page['priority']}</priority>")
        xml_parts.append("  </url>")

    # Add blog posts
    for post in posts:
        xml_parts.append("  <url>")
        xml_parts.append(f"    <loc>{base_url}/blog/{post.slug}</loc>")
        if post.updated_at:
            xml_parts.append(f"    <lastmod>{post.updated_at.strftime('%Y-%m-%d')}</lastmod>")
        xml_parts.append("    <priority>0.7</priority>")
        xml_parts.append("  </url>")

    xml_parts.append("</urlset>")

    response = Response(
        content="\n".join(xml_parts),
        media_type="application/xml"
    )
    # Cache sitemap for 1 hour (3600 seconds)
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response
