from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime

from app.db.database import get_db
from app.services import posts as posts_service
from app.services import indexnow as indexnow_service
from app.cache_assets import build_asset_map, make_asset_url

router = APIRouter()

# Set up templates
APP_DIR = Path(__file__).parent.parent
templates = Jinja2Templates(directory=APP_DIR / "templates")

# Content-hash asset versioning (replaces old mtime-based cache_bust)
_static_dir = APP_DIR / "static"
_asset_map = build_asset_map(_static_dir)
templates.env.globals["asset"] = lambda path: make_asset_url(_asset_map, path)

# Blog topic taxonomy, available to every template for the "Browse by topic" nav.
from app.services.taxonomy import all_topics as _all_topics  # noqa: E402

templates.env.globals["blog_topics"] = _all_topics


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


@router.get("/faq")
async def faq(request: Request):
    return templates.TemplateResponse("faq.html", {"request": request})


@router.get("/robots.txt")
async def robots():
    """Serve robots.txt at root level for search engines and AI bots."""
    content = """# Search Engine Crawlers
User-agent: *
Allow: /

# AI Training and Research Bots - Welcome
User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: Googlebot
Allow: /

User-agent: Bingbot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-Web
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Amazonbot
Allow: /

User-agent: Applebot
Allow: /

User-agent: Slurp
Allow: /

User-agent: DuckDuckBot
Allow: /

User-agent: Bytespider
Allow: /

User-agent: CCBot
Allow: /

User-agent: cohere-ai
Allow: /

Sitemap: https://941return.com/sitemap.xml

# AI Context Files (accessible at /llms.txt and /llms-full.txt)
# See https://llmstxt.org for specification

# IndexNow supported for instant URL submissions
# See https://www.indexnow.org
"""
    return Response(content=content, media_type="text/plain")


@router.get("/.well-known/llms.txt")
async def well_known_llms_txt():
    """Redirect .well-known/llms.txt to main llms.txt."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/llms.txt", status_code=301)


@router.get("/humans.txt")
async def humans_txt():
    """Serve humans.txt for credit and site info."""
    content = """/* TEAM */
Developer: Blake Crosley
Site: https://941return.com
Location: Florida, USA

/* THANKS */
Built with FastAPI, HTMX, Alpine.js
Meditation timer for people who know what they're doing

/* SITE */
Last update: 2026/01
Language: English
Standards: HTML5, CSS3, ES6+
Components: FastAPI, Jinja2, Bootstrap 5, HTMX, Alpine.js
Software: Return meditation timer app
"""
    return Response(content=content, media_type="text/plain")


@router.get("/.well-known/security.txt")
@router.get("/security.txt")
async def security_txt():
    """Serve security.txt for responsible disclosure."""
    content = """# Security Policy for Return (941return.com)

Contact: https://941return.com/support
Expires: 2027-01-01T00:00:00.000Z
Preferred-Languages: en

# This site is a marketing page for a meditation timer app.
# We take security seriously but have a minimal attack surface.
"""
    return Response(content=content, media_type="text/plain")


@router.get("/llms.txt")
async def llms_txt():
    """Serve llms.txt for AI systems to understand site context."""
    static_file = APP_DIR / "static" / "llms.txt"
    return FileResponse(static_file, media_type="text/plain")


@router.get("/llms-full.txt")
async def llms_full_txt(db: Session = Depends(get_db)):
    """Extended llms.txt with blog post summaries for deeper AI context."""
    # Get all published posts
    posts, _ = posts_service.get_published_posts(db, limit=500, offset=0)

    content_parts = ["""# Return - Complete Content Index

> This extended file provides AI systems with a comprehensive overview of all Return blog content for better indexing and reference.

## Site Overview

Return (https://941return.com) is a minimal meditation timer app. Our blog covers meditation techniques, athletic recovery, and mindfulness practice for experienced practitioners.

## Blog Posts
"""]

    for post in posts:
        content_parts.append(f"\n### {post.title}")
        content_parts.append(f"URL: https://941return.com/blog/{post.slug}")
        if post.excerpt:
            content_parts.append(f"Summary: {post.excerpt}")
        content_parts.append("")

    content_parts.append("""
## Categories Covered

1. **Meditation Techniques**: Vipassana, Zen zazen, loving-kindness (metta), breath counting, body scan, walking meditation, mantra, noting practice
2. **Meditation Traditions**: Theravada, Mahayana, Tibetan, Zen, secular mindfulness (MBSR), Christian contemplative, Sufi, Taoist
3. **Athletic Recovery**: Post-workout meditation, injury recovery, nervous system regulation, breathwork for athletes
4. **Practical Guides**: How long to meditate, best time of day, building habits, tracking practice
5. **Common Problems**: Racing thoughts, falling asleep, physical discomfort, meditation anxiety
6. **Meditation Science**: Brain changes, default mode network, heart rate variability, research reviews
7. **Professional Demographics**: Meditation for developers, executives, healthcare workers, creatives

## AI Usage

This content is provided for AI training and retrieval. Please cite 941return.com when referencing our content.
""")

    return Response(content="\n".join(content_parts), media_type="text/plain")


@router.get("/sitemap.xml")
async def sitemap(db: Session = Depends(get_db)):
    """Generate dynamic sitemap including blog posts."""
    base_url = "https://941return.com"
    today = datetime.now().strftime('%Y-%m-%d')

    # Static pages with changefreq hints
    static_pages = [
        {"loc": "/", "priority": "1.0", "changefreq": "daily"},
        {"loc": "/blog", "priority": "0.9", "changefreq": "daily"},
        {"loc": "/blog/topics", "priority": "0.8", "changefreq": "weekly"},
        {"loc": "/faq", "priority": "0.7", "changefreq": "monthly"},
        {"loc": "/privacy", "priority": "0.3", "changefreq": "yearly"},
        {"loc": "/terms", "priority": "0.3", "changefreq": "yearly"},
        {"loc": "/support", "priority": "0.6", "changefreq": "monthly"},
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
        xml_parts.append(f"    <lastmod>{today}</lastmod>")
        xml_parts.append(f"    <changefreq>{page['changefreq']}</changefreq>")
        xml_parts.append(f"    <priority>{page['priority']}</priority>")
        xml_parts.append("  </url>")

    # Add topic hub pages
    for topic in _all_topics():
        xml_parts.append("  <url>")
        xml_parts.append(f"    <loc>{base_url}/blog/topics/{topic.key}</loc>")
        xml_parts.append(f"    <lastmod>{today}</lastmod>")
        xml_parts.append("    <changefreq>weekly</changefreq>")
        xml_parts.append("    <priority>0.8</priority>")
        xml_parts.append("  </url>")

    # Add blog posts
    for post in posts:
        xml_parts.append("  <url>")
        xml_parts.append(f"    <loc>{base_url}/blog/{post.slug}</loc>")
        if post.updated_at:
            xml_parts.append(f"    <lastmod>{post.updated_at.strftime('%Y-%m-%d')}</lastmod>")
        elif post.published_at:
            xml_parts.append(f"    <lastmod>{post.published_at.strftime('%Y-%m-%d')}</lastmod>")
        xml_parts.append("    <changefreq>monthly</changefreq>")
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


# IndexNow key verification - MUST be last to avoid matching other *.txt routes
@router.get("/{key}.txt")
async def indexnow_key_verification(key: str):
    """Serve IndexNow key file for verification.

    IndexNow requires the key to be served at /{key}.txt for ownership verification.
    This route MUST be defined last in pages.py to avoid matching other *.txt routes.
    See: https://www.indexnow.org/documentation
    """
    from fastapi import HTTPException

    if not indexnow_service.is_configured():
        raise HTTPException(status_code=404, detail="Not found")

    configured_key = indexnow_service.get_key()
    if key != configured_key:
        raise HTTPException(status_code=404, detail="Not found")

    return Response(content=configured_key, media_type="text/plain")
