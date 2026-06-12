"""FastAPI Web 应用入口。"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="CoupangAds", version="0.1.0")

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

templates = Jinja2Templates(directory=TEMPLATES_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")
