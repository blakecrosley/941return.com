from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path
import subprocess

router = APIRouter()

# Set up templates
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

# Cache bust using git commit hash (computed once at startup)
try:
    CACHE_BUST = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"],
        stderr=subprocess.DEVNULL
    ).decode().strip()
except Exception:
    CACHE_BUST = "1"  # Fallback

# Make cache_bust available in all templates
templates.env.globals["cache_bust"] = CACHE_BUST


@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/privacy")
async def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})


@router.get("/terms")
async def terms(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})


@router.get("/support")
async def support(request: Request):
    return templates.TemplateResponse("support.html", {"request": request})
