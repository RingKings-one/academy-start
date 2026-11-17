from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.trial import router as trial_router

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"
INDEX_FILE = FRONTEND_DIR / "index.html"

app = FastAPI(
    title="Академия Старт",
    version="0.2.0",
    docs_url="/docs" if settings.is_local else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trial_router)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "env": settings.app_env,
        "tz": settings.app_tz,
    }


@app.get("/", response_class=HTMLResponse)
async def index(_: Request):
    if not INDEX_FILE.exists():
        return HTMLResponse(
            "<h1>Академия Старт</h1><p>frontend/index.html не найден</p>",
            status_code=500,
        )
    return FileResponse(INDEX_FILE)
