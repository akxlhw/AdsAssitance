"""FastAPI Web 应用入口。"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from coupangads.web.api import router as api_router

app = FastAPI(title="CoupangAds", version="1.0.0")

app.include_router(api_router)

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

templates = Jinja2Templates(directory=TEMPLATES_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/create")
def create_page(request: Request):
    """新建商品页：复用 SPA，由前端根据 URL 加载上传视图。"""
    return templates.TemplateResponse(request, "index.html")


@app.get("/progress/{product_id}")
def progress_page(request: Request, product_id: str):
    """进度页：复用 SPA，由前端根据 URL 加载进度视图。"""
    return templates.TemplateResponse(request, "index.html")


@app.get("/result/{product_id}")
def result_page(request: Request, product_id: str):
    """结果页：复用 SPA，由前端根据 URL 加载结果。"""
    return templates.TemplateResponse(request, "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
