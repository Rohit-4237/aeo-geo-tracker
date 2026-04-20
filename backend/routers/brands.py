from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from database import get_db
from models import BrandConfig

router = APIRouter(prefix="/brands", tags=["brands"])


class BrandIn(BaseModel):
    name: str
    url: str
    is_primary: bool = False


@router.get("/")
async def list_brands(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BrandConfig).order_by(BrandConfig.is_primary.desc(), BrandConfig.id))
    return [{"id": b.id, "name": b.name, "url": b.url, "is_primary": b.is_primary} for b in result.scalars()]


@router.post("/")
async def save_brands(brands: list[BrandIn], db: AsyncSession = Depends(get_db)):
    await db.execute(delete(BrandConfig))
    for b in brands:
        db.add(BrandConfig(name=b.name, url=b.url, is_primary=b.is_primary))
    await db.commit()
    return {"saved": len(brands)}


@router.delete("/")
async def clear_brands(db: AsyncSession = Depends(get_db)):
    await db.execute(delete(BrandConfig))
    await db.commit()
    return {"cleared": True}
