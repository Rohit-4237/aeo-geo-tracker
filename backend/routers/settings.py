from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from database import get_db
from models import AppSettings
import os

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsIn(BaseModel):
    api_mode: str        # "byok" | "platform"
    openai_key: str | None = None
    gemini_key: str | None = None
    perplexity_key: str | None = None


@router.get("/")
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AppSettings).where(AppSettings.id == 1))
    s = result.scalar_one_or_none()
    platform_keys_configured = bool(
        os.getenv("PLATFORM_OPENAI_API_KEY") or
        os.getenv("PLATFORM_GEMINI_API_KEY") or
        os.getenv("PLATFORM_PERPLEXITY_API_KEY")
    )
    if not s:
        return {
            "api_mode": "byok",
            "openai_key": None,
            "gemini_key": None,
            "perplexity_key": None,
            "platform_keys_configured": platform_keys_configured,
        }
    return {
        "api_mode": s.api_mode,
        "openai_key": "***" if s.openai_key else None,
        "gemini_key": "***" if s.gemini_key else None,
        "perplexity_key": "***" if s.perplexity_key else None,
        "platform_keys_configured": platform_keys_configured,
    }


@router.post("/")
async def save_settings(data: SettingsIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AppSettings).where(AppSettings.id == 1))
    s = result.scalar_one_or_none()
    if not s:
        s = AppSettings(id=1)
        db.add(s)
    s.api_mode = data.api_mode
    if data.openai_key and data.openai_key != "***":
        s.openai_key = data.openai_key
    if data.gemini_key and data.gemini_key != "***":
        s.gemini_key = data.gemini_key
    if data.perplexity_key and data.perplexity_key != "***":
        s.perplexity_key = data.perplexity_key
    await db.commit()
    return {"saved": True}
