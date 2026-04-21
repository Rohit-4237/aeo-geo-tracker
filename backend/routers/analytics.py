from collections import defaultdict

from fastapi import APIRouter, HTTPException
from firebase_db import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _check_run(run_id: str, db):
    doc = db.collection("tracking_runs").document(run_id).get()
    if not doc.exists:
        raise HTTPException(404, "Run not found")
    return doc.to_dict()


def _get_results(run_id: str, db) -> list[dict]:
    docs = db.collection("prompt_results").where("run_id", "==", run_id).stream()
    return [d.to_dict() for d in docs]


def _get_brands(db) -> list[dict]:
    docs = db.collection("brand_configs").stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]


def _get_prompts(db) -> list[dict]:
    docs = db.collection("prompts").order_by("order_index").stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/{run_id}/overview/")
def overview(run_id: str):
    """Total mentions and citations per brand across all platforms."""
    db = get_db()
    _check_run(run_id, db)
    results = _get_results(run_id, db)
    brands = _get_brands(db)

    totals = {b["name"]: {"mentions": 0, "citations": 0} for b in brands}
    for r in results:
        for brand, count in (r.get("brand_mentions") or {}).items():
            if brand in totals:
                totals[brand]["mentions"] += count
        for brand, urls in (r.get("cited_urls") or {}).items():
            if brand in totals:
                totals[brand]["citations"] += len(urls)

    return {"brands": brands, "totals": totals}


@router.get("/{run_id}/by-prompt/")
def by_prompt(run_id: str, platform: str | None = None):
    """Mentions per brand, per prompt, optionally filtered by platform."""
    db = get_db()
    _check_run(run_id, db)
    results = _get_results(run_id, db)
    prompts = _get_prompts(db)

    prompt_map = {p["id"]: p for p in prompts}
    data: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    seen: dict = defaultdict(set)  # prompt_id → set of platforms

    for r in results:
        if platform and r.get("platform") != platform:
            continue
        pid = r.get("prompt_id")
        plat = r.get("platform")
        seen[pid].add(plat)
        for brand, count in (r.get("brand_mentions") or {}).items():
            data[pid][plat][brand] += count

    # Ensure every prompt+platform combo appears even if mentions == 0
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
def citations(run_id: str):
    """Cited pages per brand per prompt."""
    db = get_db()
    _check_run(run_id, db)
    results = _get_results(run_id, db)
    prompts = _get_prompts(db)

    prompt_map = {p["id"]: p for p in prompts}
    data: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))

    for r in results:
        for brand, urls in (r.get("cited_urls") or {}).items():
            for u in urls:
                data[r["prompt_id"]][r["platform"]][brand].add(u)

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
def sentiment(run_id: str):
    """Sentiment breakdown per brand across all platforms."""
    db = get_db()
    _check_run(run_id, db)
    results = _get_results(run_id, db)
    brands = _get_brands(db)

    counts = {b["name"]: {"positive": 0, "negative": 0, "neutral": 0} for b in brands}
    primary = next((b["name"] for b in brands if b.get("is_primary")), None)

    for r in results:
        if not r.get("available") or not r.get("sentiment"):
            continue
        mentioned = [name for name, cnt in (r.get("brand_mentions") or {}).items() if cnt > 0]
        targets = mentioned if mentioned else ([primary] if primary else [])
        for name in targets:
            if name in counts:
                counts[name][r["sentiment"]] += 1

    scores = {}
    for brand, c in counts.items():
        pos, neg = c["positive"], c["negative"]
        total = pos + neg
        scores[brand] = round((pos - neg) / total, 4) if total > 0 else 0.0

    return {"counts": counts, "scores": scores}


@router.get("/{run_id}/errors/")
def errors(run_id: str):
    """Return all failed results with their error messages."""
    db = get_db()
    _check_run(run_id, db)
    results = _get_results(run_id, db)
    prompts = _get_prompts(db)

    prompt_map = {p["id"]: p["text"] for p in prompts}
    failed = [
        {
            "prompt": prompt_map.get(r.get("prompt_id"), ""),
            "platform": r.get("platform"),
            "error": r.get("error_message") or "unknown error",
        }
        for r in results
        if not r.get("available")
    ]
    return {"failed": len(failed), "errors": failed}
