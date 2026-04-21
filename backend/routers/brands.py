from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from firebase_db import get_db
from datetime import datetime, timezone

router = APIRouter(prefix="/brands", tags=["brands"])


class BrandIn(BaseModel):
    name: str
    url: str
    is_primary: bool = False


@router.get("")
def list_brands():
    db = get_db()
    docs = db.collection("brand_configs").stream()
    result = [{"id": d.id, **d.to_dict()} for d in docs]
    # Sort in Python: primary brand first, then by creation time
    result.sort(key=lambda x: (not x.get("is_primary", False), x.get("created_at", "")))
    return result


@router.post("")
def save_brands(brands: list[BrandIn]):
    db = get_db()
    col = db.collection("brand_configs")
    # Delete all existing brands
    for doc in col.stream():
        doc.reference.delete()
    # Insert new set
    now = datetime.now(timezone.utc).isoformat()
    for b in brands:
        col.add({"name": b.name, "url": b.url, "is_primary": b.is_primary, "created_at": now})
    return {"saved": len(brands)}


@router.delete("")
def clear_brands():
    db = get_db()
    for doc in db.collection("brand_configs").stream():
        doc.reference.delete()
    return {"cleared": True}
