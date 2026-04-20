import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from database import get_db, AsyncSessionLocal
from models import TrackingRun, PromptResult, Prompt, BrandConfig, AppSettings
import os

router = APIRouter(prefix="/runs", tags=["runs"])

PLATFORMS = ["chatgpt", "gemini", "perplexity", "google_aio", "google_aim"]


class RunRequest(BaseModel):
    name: str
    platforms: list[str]


@router.get("/")
async def list_runs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TrackingRun).order_by(TrackingRun.created_at.desc()))
    return [
        {
            "id": r.id, "name": r.name, "platforms": r.platforms,
            "status": r.status, "total_prompts": r.total_prompts,
            "completed_prompts": r.completed_prompts,
            "created_at": r.created_at.isoformat(),
        }
        for r in result.scalars()
    ]


@router.post("/")
async def start_run(req: RunRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    invalid = [p for p in req.platforms if p not in PLATFORMS]
    if invalid:
        raise HTTPException(400, f"Invalid platforms: {invalid}")

    prompts_result = await db.execute(select(Prompt).order_by(Prompt.order_index))
    prompts = prompts_result.scalars().all()
    if not prompts:
        raise HTTPException(400, "No prompts loaded. Upload a CSV first.")

    brands_result = await db.execute(select(BrandConfig))
    brands = brands_result.scalars().all()
    if not brands:
        raise HTTPException(400, "No brands configured. Set up brands first.")

    run = TrackingRun(
        name=req.name,
        platforms=req.platforms,
        status="pending",
        total_prompts=len(prompts) * len(req.platforms),
        completed_prompts=0,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    background_tasks.add_task(_execute_run, run.id, [p.id for p in prompts], [{"id": b.id, "name": b.name, "url": b.url, "is_primary": b.is_primary} for b in brands], req.platforms)

    return {"run_id": run.id, "status": "started"}


@router.get("/{run_id}/")
async def get_run(run_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TrackingRun).where(TrackingRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")
    return {
        "id": run.id, "name": run.name, "platforms": run.platforms,
        "status": run.status, "total_prompts": run.total_prompts,
        "completed_prompts": run.completed_prompts,
        "created_at": run.created_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


@router.delete("/{run_id}/")
async def delete_run(run_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TrackingRun).where(TrackingRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")
    await db.delete(run)
    await db.commit()
    return {"deleted": True}


async def _get_api_keys():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AppSettings).where(AppSettings.id == 1))
        s = result.scalar_one_or_none()
        mode = s.api_mode if s else "byok"
        if mode == "platform":
            return {
                "openai": os.getenv("PLATFORM_OPENAI_API_KEY", ""),
                "gemini": os.getenv("PLATFORM_GEMINI_API_KEY", ""),
                "perplexity": os.getenv("PLATFORM_PERPLEXITY_API_KEY", ""),
            }
        return {
            "openai": s.openai_key or "" if s else "",
            "gemini": s.gemini_key or "" if s else "",
            "perplexity": s.perplexity_key or "" if s else "",
        }


async def _execute_run(run_id: int, prompt_ids: list[int], brands: list[dict], platforms: list[str]):
    from services import openai_service, gemini_service, perplexity_service, google_scraper

    async with AsyncSessionLocal() as db:
        run_result = await db.execute(select(TrackingRun).where(TrackingRun.id == run_id))
        run = run_result.scalar_one()
        run.status = "running"
        await db.commit()

    keys = await _get_api_keys()

    async with AsyncSessionLocal() as db:
        prompts_result = await db.execute(select(Prompt).where(Prompt.id.in_(prompt_ids)).order_by(Prompt.order_index))
        prompts = prompts_result.scalars().all()

    completed = 0
    for prompt in prompts:
        tasks = {}
        for platform in platforms:
            if platform == "chatgpt" and keys["openai"]:
                tasks[platform] = openai_service.query(prompt.text, brands, keys["openai"])
            elif platform == "gemini" and keys["gemini"]:
                tasks[platform] = gemini_service.query(prompt.text, brands, keys["gemini"])
            elif platform == "perplexity" and keys["perplexity"]:
                tasks[platform] = perplexity_service.query(prompt.text, brands, keys["perplexity"])
            elif platform == "google_aio":
                tasks[platform] = google_scraper.query_ai_overview(prompt.text, brands)
            elif platform == "google_aim":
                tasks[platform] = google_scraper.query_ai_mode(prompt.text, brands)
            else:
                tasks[platform] = _no_key_result(platform)

        results = await asyncio.gather(*[tasks[p] for p in platforms], return_exceptions=True)

        async with AsyncSessionLocal() as db:
            for platform, result in zip(platforms, results):
                if isinstance(result, Exception):
                    result = {"available": False, "error": str(result), "raw_response": "", "brand_mentions": {}, "cited_urls": {}, "sentiment": "neutral", "sentiment_score": 0.0}
                db.add(PromptResult(
                    run_id=run_id,
                    prompt_id=prompt.id,
                    platform=platform,
                    raw_response=result.get("raw_response", ""),
                    available=result.get("available", False),
                    brand_mentions=result.get("brand_mentions", {}),
                    cited_urls=result.get("cited_urls", {}),
                    sentiment=result.get("sentiment", "neutral"),
                    sentiment_score=result.get("sentiment_score", 0.0),
                    error_message=result.get("error") if not result.get("available") else None,
                ))
                completed += 1

            run_result = await db.execute(select(TrackingRun).where(TrackingRun.id == run_id))
            run = run_result.scalar_one()
            run.completed_prompts = completed
            await db.commit()

    async with AsyncSessionLocal() as db:
        run_result = await db.execute(select(TrackingRun).where(TrackingRun.id == run_id))
        run = run_result.scalar_one()
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        await db.commit()


async def _no_key_result(platform: str) -> dict:
    return {
        "available": False,
        "raw_response": "",
        "brand_mentions": {},
        "cited_urls": {},
        "sentiment": "neutral",
        "sentiment_score": 0.0,
        "error": f"No API key configured for {platform}",
    }
