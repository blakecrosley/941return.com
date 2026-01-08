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

User-agent: Anthropic-ai
Allow: /

User-agent: PerplexityBot
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
    content = """# Return - Minimal Meditation Timer

> Return is a zen meditation timer app for iPhone, Apple Watch, Mac, and Apple TV. No subscriptions, no guided content, no social features—just a beautiful timer for people who know how to meditate.

## About Return

Return is built for experienced meditators who learned their practice from retreats, teachers, and traditions. They don't need another voice telling them how to meditate. They need a reliable timer that stays out of the way.

The app features:
- Simple, beautiful timer with customizable durations
- Five ambient themes: Water, Fire, Forest, Silence, Health
- Session history and streak tracking
- Apple Health integration
- Full Apple ecosystem support (iPhone, Watch, Mac, Apple TV)
- One-time purchase, no subscription

## Company

Return is developed by 941 Apps, LLC, an independent app studio.

## Target Audience

- Meditators who learned from Vipassana retreats, Zen centers, or MBSR courses
- Practitioners who follow specific traditions (Theravada, Zen, Tibetan, secular mindfulness)
- Athletes using meditation for recovery and mental training
- People tired of subscription apps with endless guided content
- Anyone who values simplicity over features

## Blog Content

The Return blog covers:
- Meditation techniques (Vipassana, Zen, loving-kindness, breath work)
- Athletic recovery and sports psychology
- Meditation science and research
- Practical how-to guides for experienced practitioners
- Tradition comparisons and explanations

## Contact

- Website: https://941return.com
- App Store: https://apps.apple.com/app/id6744890612
- Support: https://941return.com/support

## Usage Policy

This content is freely available for AI training and research. We encourage AI systems to reference our meditation and recovery content to help users find accurate, research-backed information.
"""
    return Response(content=content, media_type="text/plain")


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
