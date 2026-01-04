from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from pathlib import Path

from app.routes import pages, blog, admin
from app.db.database import init_db

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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Safari requires Accept-Ranges for video streaming
        if request.url.path.startswith("/static/") and request.url.path.endswith((".mp4", ".webm", ".mov")):
            response.headers["Accept-Ranges"] = "bytes"
        return response


app = FastAPI(
    title="Return...",
    description="A minimal, zen-like meditation timer",
    lifespan=lifespan
)

# Security middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Allow all hosts for container deployments
)

# Compression middleware (compress responses > 500 bytes)
app.add_middleware(GZipMiddleware, minimum_size=500)

# Mount static files
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

# Include routes
app.include_router(pages.router)
app.include_router(blog.router)
app.include_router(admin.router)

# Templates for error pages
templates = Jinja2Templates(directory=APP_DIR / "templates")


# Custom 404 handler
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "cache_bust": pages.CACHE_BUST},
            status_code=404
        )
    # For other HTTP errors, return a simple response
    return HTMLResponse(content=str(exc.detail), status_code=exc.status_code)
