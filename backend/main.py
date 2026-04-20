from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os

load_dotenv()

from database import init_db
from routers import brands, prompts, tracking, analytics, settings

app = FastAPI(title="AEO/GEO Tracker API", version="1.0.0")

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(brands.router)
app.include_router(prompts.router)
app.include_router(tracking.router)
app.include_router(analytics.router)
app.include_router(settings.router)


FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(os.path.join(FRONTEND_DIR, "static")):
    app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "static")), name="static")


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/health")
async def health():
    return {"status": "ok"}


_API_PREFIXES = ("brands", "prompts", "runs", "analytics", "settings", "health", "docs", "openapi", "static")


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    if any(full_path.startswith(p) for p in _API_PREFIXES):
        from fastapi import HTTPException
        raise HTTPException(404)
    index = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"error": "Frontend not found"}
