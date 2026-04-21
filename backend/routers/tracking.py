"""
Tracking runs — Firestore-backed, fully synchronous.

Two-step execution model (Vercel-friendly):
  1. POST /runs/          → creates the run document, returns {run_id} immediately.
  2. POST /runs/{id}/execute/ → performs the actual AI queries (long-running,
                                Vercel maxDuration: 300 s).
     The frontend fires step 2 without awaiting so the UI stays responsive;
     it polls GET /runs/{id}/ to track live progress written to Firestore.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from firebase_db import get_db

router = APIRouter(prefix="/runs", tags=["runs"])

PLATFORMS = ["chatgpt", "gemini", "perplexity", "google_aio", "google_aim"]


class RunRequest(BaseModel):
    name: str
    platforms: list[str]


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("/")
def list_runs():
    db = get_db()
    docs = (
        db.collection("tracking_runs")
        .order_by("created_at", direction="DESCENDING")
        .stream()
    )
    return [{"id": d.id, **d.to_dict()} for d in docs]


@router.post("/")
def start_run(req: RunRequest):
    invalid = [p for p in req.platforms if p not in PLATFORMS]
    if invalid:
        raise HTTPException(400, f"Invalid platforms: {invalid}")

    db = get_db()

    prompts_docs = list(db.collection("prompts").stream())
    if not prompts_docs:
        raise HTTPException(400, "No prompts loaded. Upload a CSV first.")

    brands_docs = list(db.collection("brand_configs").stream())
    if not brands_docs:
        raise HTTPException(400, "No brands configured. Set up brands first.")

    prompts = [{"id": d.id, **d.to_dict()} for d in prompts_docs]

    now = datetime.now(timezone.utc).isoformat()
    _, run_ref = db.collection("tracking_runs").add({
        "name": req.name,
        "platforms": req.platforms,
        "status": "pending",
        "total_prompts": len(prompts) * len(req.platforms),
        "completed_prompts": 0,
        "created_at": now,
        "completed_at": None,
    })
    return {"run_id": run_ref.id, "status": "pending"}


@router.get("/{run_id}/")
def get_run(run_id: str):
    db = get_db()
    doc = db.collection("tracking_runs").document(run_id).get()
    if not doc.exists:
        raise HTTPException(404, "Run not found")
    return {"id": doc.id, **doc.to_dict()}


@router.delete("/{run_id}/")
def delete_run(run_id: str):
    db = get_db()
    if not db.collection("tracking_runs").document(run_id).get().exists:
        raise HTTPException(404, "Run not found")
    # Delete child results first
    for r in db.collection("prompt_results").where("run_id", "==", run_id).stream():
        r.reference.delete()
    db.collection("tracking_runs").document(run_id).delete()
    return {"deleted": True}


# ── Execute endpoint (long-running, maxDuration: 300 s) ───────────────────────

@router.post("/{run_id}/execute/")
def execute_run(run_id: str):
    """
    Performs the AI queries for a run created by POST /runs/.
    Called by the frontend immediately after receiving the run_id,
    without awaiting (fire-and-forget from the JS side).
    Writes progress to Firestore so GET /runs/{id}/ reflects live state.
    """
    db = get_db()
    run_doc = db.collection("tracking_runs").document(run_id).get()
    if not run_doc.exists:
        raise HTTPException(404, "Run not found")

    run_data = run_doc.to_dict()
    platforms: list[str] = run_data["platforms"]

    prompts = sorted(
        [{"id": d.id, **d.to_dict()} for d in db.collection("prompts").stream()],
        key=lambda p: p.get("order_index", 0),
    )
    brands = [{"id": d.id, **d.to_dict()} for d in db.collection("brand_configs").stream()]
    keys = _get_api_keys(db)

    run_ref = db.collection("tracking_runs").document(run_id)
    run_ref.update({"status": "running"})

    try:
        _do_execute(run_id, prompts, brands, platforms, keys, db)
        run_ref.update({
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        run_ref.update({
            "status": "failed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "error": str(exc),
        })
        raise

    return {"status": "completed"}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_api_keys(db) -> dict:
    doc = db.collection("app_settings").document("main").get()
    if doc.exists:
        s = doc.to_dict()
        if s.get("api_mode") == "platform":
            return {
                "openai": os.getenv("PLATFORM_OPENAI_API_KEY", ""),
                "gemini": os.getenv("PLATFORM_GEMINI_API_KEY", ""),
                "perplexity": os.getenv("PLATFORM_PERPLEXITY_API_KEY", ""),
            }
        return {
            "openai": s.get("openai_key") or "",
            "gemini": s.get("gemini_key") or "",
            "perplexity": s.get("perplexity_key") or "",
        }
    return {
        "openai": os.getenv("PLATFORM_OPENAI_API_KEY", ""),
        "gemini": os.getenv("PLATFORM_GEMINI_API_KEY", ""),
        "perplexity": os.getenv("PLATFORM_PERPLEXITY_API_KEY", ""),
    }


def _do_execute(
    run_id: str,
    prompts: list[dict],
    brands: list[dict],
    platforms: list[str],
    keys: dict,
    db,
) -> None:
    from services import gemini_service, google_scraper, openai_service, perplexity_service

    results_col = db.collection("prompt_results")
    run_ref = db.collection("tracking_runs").document(run_id)
    completed = 0

    for prompt in prompts:
        for platform in platforms:
            try:
                if platform == "chatgpt" and keys["openai"]:
                    result = openai_service.query(prompt["text"], brands, keys["openai"])
                elif platform == "gemini" and keys["gemini"]:
                    result = gemini_service.query(prompt["text"], brands, keys["gemini"])
                elif platform == "perplexity" and keys["perplexity"]:
                    result = perplexity_service.query(prompt["text"], brands, keys["perplexity"])
                elif platform in ("google_aio", "google_aim"):
                    result = google_scraper.query(prompt["text"], brands, platform)
                else:
                    result = _no_key_result(platform)
            except Exception as exc:
                result = _error_result(str(exc))

            results_col.add({
                "run_id": run_id,
                "prompt_id": prompt["id"],
                "platform": platform,
                "raw_response": result.get("raw_response", ""),
                "available": result.get("available", False),
                "brand_mentions": result.get("brand_mentions", {}),
                "cited_urls": result.get("cited_urls", {}),
                "sentiment": result.get("sentiment", "neutral"),
                "sentiment_score": result.get("sentiment_score", 0.0),
                "error_message": result.get("error") if not result.get("available") else None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            completed += 1
            run_ref.update({"completed_prompts": completed})


def _no_key_result(platform: str) -> dict:
    return {
        "available": False,
        "raw_response": "",
        "brand_mentions": {},
        "cited_urls": {},
        "sentiment": "neutral",
        "sentiment_score": 0.0,
        "error": f"No API key configured for {platform}",
    }


def _error_result(error: str) -> dict:
    return {
        "available": False,
        "raw_response": "",
        "brand_mentions": {},
        "cited_urls": {},
        "sentiment": "neutral",
        "sentiment_score": 0.0,
        "error": error,
    }
