from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.routes import pages

# Get the app directory
APP_DIR = Path(__file__).parent

app = FastAPI(
    title="Return...",
    description="A minimal, zen-like meditation timer"
)

# Mount static files
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

# Include routes
app.include_router(pages.router)
