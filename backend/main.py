from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os

load_dotenv()

from routers import brands, prompts, tracking, analytics, settings  # noqa: E402

app = FastAPI(title="AEO/GEO Tracker API", version="1.0.0", redirect_slashes=False)

# Allow all origins by default — tighten via CORS_ORIGINS env var if needed
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
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


@app.get("/health")
def health():
    return {"status": "ok"}


# ── Local-dev static file serving ─────────────────────────────────────────────
# On Vercel, static files in public/ are served directly by the CDN;
# this block only kicks in for `uvicorn` local runs.
_FRONTEND_CANDIDATES = [
    os.path.join(os.path.dirname(__file__), "..", "public"),
    os.path.join(os.path.dirname(__file__), "..", "frontend"),
]
FRONTEND_DIR = next((d for d in _FRONTEND_CANDIDATES if os.path.isdir(d)), None)

if FRONTEND_DIR and os.path.exists(os.path.join(FRONTEND_DIR, "static")):
    app.mount(
        "/static",
        StaticFiles(directory=os.path.join(FRONTEND_DIR, "static")),
        name="static",
    )

_API_PREFIXES = (
    "brands", "prompts", "runs", "analytics", "settings",
    "health", "docs", "openapi", "static",
)


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    if any(full_path.startswith(p) for p in _API_PREFIXES):
        from fastapi import HTTPException
        raise HTTPException(404)
    if FRONTEND_DIR:
        index = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index):
            return FileResponse(index)
    return {"error": "Frontend not found"}
