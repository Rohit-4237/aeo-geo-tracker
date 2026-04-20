from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import TrackingRun, PromptResult, Prompt, BrandConfig
from collections import defaultdict

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/{run_id}/overview/")
async def overview(run_id: int, db: AsyncSession = Depends(get_db)):
    """Total mentions and citations per brand across all platforms."""
    await _check_run(run_id, db)
    results = await _get_results(run_id, db)
    brands = await _get_brands(db)

    totals = {b["name"]: {"mentions": 0, "citations": 0} for b in brands}
    for r in results:
        for brand, count in (r.brand_mentions or {}).items():
            if brand in totals:
                totals[brand]["mentions"] += count
        for brand, urls in (r.cited_urls or {}).items():
            if brand in totals:
                totals[brand]["citations"] += len(urls)

    return {"brands": brands, "totals": totals}


@router.get("/{run_id}/by-prompt/")
async def by_prompt(run_id: int, platform: str | None = None, db: AsyncSession = Depends(get_db)):
    """Mentions per brand, per prompt, optionally filtered by platform."""
    await _check_run(run_id, db)
    results = await _get_results(run_id, db)
    prompts = await _get_prompts(db)

    prompt_map = {p["id"]: p for p in prompts}
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    seen = defaultdict(set)  # pid -> set of platforms that have a result

    for r in results:
        if platform and r.platform != platform:
            continue
        pid = r.prompt_id
        seen[pid].add(r.platform)
        for brand, count in (r.brand_mentions or {}).items():
            data[pid][r.platform][brand] += count

    # ensure every prompt+platform with a result appears even if mentions=0
    for pid, plats in seen.items():
        for plat in plats:
            if plat not in data[pid]:
                data[pid][plat]  # touch to create empty defaultdict

    return {
        "prompts": [
            {
                "id": pid,
                "text": prompt_map.get(pid, {}).get("text", ""),
                "category": prompt_map.get(pid, {}).get("category"),
                "platforms": {plat: dict(brands) for plat, brands in plat_data.items()},
            }
            for pid, plat_data in data.items()
        ]
    }


@router.get("/{run_id}/citations/")
async def citations(run_id: int, db: AsyncSession = Depends(get_db)):
    """Cited pages per brand per prompt."""
    await _check_run(run_id, db)
    results = await _get_results(run_id, db)
    prompts = await _get_prompts(db)

    prompt_map = {p["id"]: p for p in prompts}
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))

    for r in results:
        for brand, urls in (r.cited_urls or {}).items():
            for u in urls:
                data[r.prompt_id][r.platform][brand].add(u)

    return {
        "prompts": [
            {
                "id": pid,
                "text": prompt_map.get(pid, {}).get("text", ""),
                "category": prompt_map.get(pid, {}).get("category"),
                "platforms": {
                    plat: {brand: list(urls) for brand, urls in brands.items()}
                    for plat, brands in platforms.items()
                },
            }
            for pid, platforms in data.items()
        ]
    }


@router.get("/{run_id}/sentiment/")
async def sentiment(run_id: int, db: AsyncSession = Depends(get_db)):
    """Sentiment breakdown per brand across all platforms."""
    await _check_run(run_id, db)
    results = await _get_results(run_id, db)
    brands = await _get_brands(db)

    counts = {b["name"]: {"positive": 0, "negative": 0, "neutral": 0} for b in brands}
    primary = next((b["name"] for b in brands if b.get("is_primary")), None)

    # Sentiment is per-response (not per brand), attach to primary brand
    for r in results:
        if not r.available or not r.sentiment:
            continue
        # Attribute sentiment to brands that were mentioned in this response
        mentioned = [name for name, cnt in (r.brand_mentions or {}).items() if cnt > 0]
        targets = mentioned if mentioned else ([primary] if primary else [])
        for name in targets:
            if name in counts:
                counts[name][r.sentiment] += 1

    scores = {}
    for brand, c in counts.items():
        pos, neg = c["positive"], c["negative"]
        total = pos + neg
        scores[brand] = round((pos - neg) / total, 4) if total > 0 else 0.0

    return {"counts": counts, "scores": scores}


@router.get("/{run_id}/errors/")
async def errors(run_id: int, db: AsyncSession = Depends(get_db)):
    """Return all failed results with their error messages."""
    await _check_run(run_id, db)
    results = await _get_results(run_id, db)
    prompts = await _get_prompts(db)
    prompt_map = {p["id"]: p["text"] for p in prompts}
    failed = [
        {
            "prompt": prompt_map.get(r.prompt_id, ""),
            "platform": r.platform,
            "error": r.error_message or "unknown error",
        }
        for r in results if not r.available
    ]
    return {"failed": len(failed), "errors": failed}


# ── helpers ──────────────────────────────────────────────────────────────────

async def _check_run(run_id: int, db: AsyncSession):
    result = await db.execute(select(TrackingRun).where(TrackingRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")
    return run


async def _get_results(run_id: int, db: AsyncSession):
    result = await db.execute(select(PromptResult).where(PromptResult.run_id == run_id))
    return result.scalars().all()


async def _get_brands(db: AsyncSession):
    result = await db.execute(select(BrandConfig))
    return [{"id": b.id, "name": b.name, "url": b.url, "is_primary": b.is_primary} for b in result.scalars()]


async def _get_prompts(db: AsyncSession):
    result = await db.execute(select(Prompt).order_by(Prompt.order_index))
    return [{"id": p.id, "text": p.text, "category": p.category} for p in result.scalars()]
