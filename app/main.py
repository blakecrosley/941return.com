from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Header
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, FileResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from pathlib import Path
from typing import Optional
import os
import re

from app.routes import pages, blog, admin, api
from app.db.database import init_db
from app.security.headers import SecurityHeadersMiddleware
from app.security.logging import SecurityLogMiddleware
from app.security.rate_limit import RateLimitMiddleware

# Analytics (optional - only loads if configured)
analytics = None
ANALYTICS_WORKER_URL = os.getenv("ANALYTICS_WORKER_URL", "")
ANALYTICS_D1_DATABASE_ID = os.getenv("ANALYTICS_D1_DATABASE_ID", "")
ANALYTICS_CF_ACCOUNT_ID = os.getenv("ANALYTICS_CF_ACCOUNT_ID", "")
ANALYTICS_CF_API_TOKEN = os.getenv("ANALYTICS_CF_API_TOKEN", "")
ANALYTICS_PASSKEY = os.getenv("ANALYTICS_PASSKEY", "")

if all([ANALYTICS_WORKER_URL, ANALYTICS_D1_DATABASE_ID, ANALYTICS_CF_ACCOUNT_ID, ANALYTICS_CF_API_TOKEN]):
    try:
        from analytics_941 import setup_analytics
        analytics = setup_analytics(
            site_name="941return.com",
            worker_url=ANALYTICS_WORKER_URL,
            d1_database_id=ANALYTICS_D1_DATABASE_ID,
            cf_account_id=ANALYTICS_CF_ACCOUNT_ID,
            cf_api_token=ANALYTICS_CF_API_TOKEN,
            passkey=ANALYTICS_PASSKEY if ANALYTICS_PASSKEY else None,
        )
    except ImportError:
        pass  # analytics_941 not installed

# Get the app directory
APP_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: Initialize database and sync content
    init_db()

    # Sync markdown files to database
    from app.db.database import SessionLocal
    from app.services.posts import sync_all_files
    db = SessionLocal()
    posts = sync_all_files(db)
    db.close()
    if posts:
        print(f"Synced {len(posts)} blog posts from markdown files")

    yield
    # Shutdown: nothing to clean up


class HeadRequestMiddleware(BaseHTTPMiddleware):
    """Handle HEAD requests by converting them to GET and stripping the body.

    FastAPI doesn't automatically support HEAD method for all routes.
    This middleware ensures HEAD requests work for SEO tools like Googlebot.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method == "HEAD":
            request.scope["method"] = "GET"
            response = await call_next(request)
            response.body = b""
            return response
        return await call_next(request)


app = FastAPI(
    title="Return...",
    description="A minimal, zen-like meditation timer",
    lifespan=lifespan
)

# Middleware
app.add_middleware(HeadRequestMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
# Configure allowed hosts from environment
# In production, set ALLOWED_HOSTS to your actual domains
# For local dev, localhost is included by default
# Note: Railway health checks use internal IPs, so we use "*" to allow them
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",") if os.getenv("ALLOWED_HOSTS") else []
DEFAULT_HOSTS = ["941return.com", "www.941return.com", "941return.com.local", "941return.test", "localhost", "127.0.0.1"]
all_allowed_hosts = list(set(ALLOWED_HOSTS + DEFAULT_HOSTS)) if ALLOWED_HOSTS else DEFAULT_HOSTS

# Allow all hosts in Railway (health checks use internal IPs)
# TrustedHostMiddleware with "*" still provides CSRF protection via other headers
if os.getenv("RAILWAY_ENVIRONMENT"):
    all_allowed_hosts = ["*"]

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=all_allowed_hosts
)

# Compression middleware (compress responses > 500 bytes)
app.add_middleware(GZipMiddleware, minimum_size=500)

# Security logging (registered last so it runs first on request, last on response)
app.add_middleware(SecurityLogMiddleware, site_name="941return.com")

# Video route with proper range request support for Safari
@app.get("/static/videos/{filename}")
async def serve_video(filename: str, range_header: Optional[str] = Header(None, alias="Range")):
    """Serve video files with Range request support for Safari."""
    # Security: Sanitize filename to prevent path traversal
    # Only allow the basename (no directories) and validate extension
    safe_filename = os.path.basename(filename)
    if not safe_filename or safe_filename != filename:
        return Response(status_code=404)

    # Only allow specific video extensions
    if not safe_filename.endswith((".mp4", ".webm", ".mov")):
        return Response(status_code=404)

    # Build path and verify it's within the videos directory
    videos_dir = (APP_DIR / "static" / "videos").resolve()
    video_path = (videos_dir / safe_filename).resolve()

    # Security: Ensure the resolved path is within videos directory
    if not str(video_path).startswith(str(videos_dir)):
        return Response(status_code=404)

    if not video_path.exists():
        return Response(status_code=404)

    file_size = os.path.getsize(video_path)

    # Common headers for Safari compatibility - bypass CDN cache
    base_headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": "video/mp4",
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
    }

    # Handle range requests (required for Safari video streaming)
    if range_header:
        range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
            end = min(end, file_size - 1)
            length = end - start + 1

            with open(video_path, "rb") as f:
                f.seek(start)
                data = f.read(length)

            return Response(
                content=data,
                status_code=206,
                headers={
                    **base_headers,
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Content-Length": str(length),
                },
            )

    # Full file response
    return FileResponse(
        video_path,
        media_type="video/mp4",
        headers={
            **base_headers,
            "Content-Length": str(file_size),
        }
    )

# Mount static files (videos handled by route above)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

# Include routes
app.include_router(pages.router)
app.include_router(blog.router)
app.include_router(admin.router)
app.include_router(api.router)

# Analytics dashboard (if configured)
if analytics:
    app.include_router(analytics.dashboard_router, prefix="/admin/analytics")
    # Make tracking script available in all templates
    from app.routes.pages import templates as page_templates
    page_templates.env.globals["analytics_script"] = analytics.tracking_script()
else:
    from app.routes.pages import templates as page_templates
    page_templates.env.globals["analytics_script"] = ""

# Templates for error pages (needs asset() global for base.html)
from app.cache_assets import build_asset_map, make_asset_url
_asset_map = build_asset_map(APP_DIR / "static")
templates = Jinja2Templates(directory=APP_DIR / "templates")
templates.env.globals["asset"] = lambda path: make_asset_url(_asset_map, path)

# Early Hints: preload Link header for critical CSS
app.state.preload_links = [
    f'<{make_asset_url(_asset_map, "css/custom.css")}>; rel=preload; as=style',
]


# Custom 404 handler
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "404.html",
            {"request": request},
            status_code=404
        )
    # For other HTTP errors, return a simple response
    return HTMLResponse(content=str(exc.detail), status_code=exc.status_code)
