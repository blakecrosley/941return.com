from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os

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
