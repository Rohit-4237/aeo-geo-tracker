import os
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from firebase_db import get_db

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsIn(BaseModel):
    api_mode: str  # "byok" | "platform"
    openai_key: str | None = None
    gemini_key: str | None = None
    perplexity_key: str | None = None


@router.get("/")
def get_settings():
    db = get_db()
    doc = db.collection("app_settings").document("main").get()
    platform_keys_configured = bool(
        os.getenv("PLATFORM_OPENAI_API_KEY")
        or os.getenv("PLATFORM_GEMINI_API_KEY")
        or os.getenv("PLATFORM_PERPLEXITY_API_KEY")
    )
    if not doc.exists:
        return {
            "api_mode": "byok",
            "openai_key": None,
            "gemini_key": None,
            "perplexity_key": None,
            "platform_keys_configured": platform_keys_configured,
        }
    s = doc.to_dict()
    return {
        "api_mode": s.get("api_mode", "byok"),
        "openai_key": "***" if s.get("openai_key") else None,
        "gemini_key": "***" if s.get("gemini_key") else None,
        "perplexity_key": "***" if s.get("perplexity_key") else None,
        "platform_keys_configured": platform_keys_configured,
    }


@router.post("/")
def save_settings(data: SettingsIn):
    db = get_db()
    doc_ref = db.collection("app_settings").document("main")
    doc = doc_ref.get()
    existing = doc.to_dict() if doc.exists else {}

    payload = {
        "api_mode": data.api_mode,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        # Only overwrite key fields if a real (non-masked) value was sent
        "openai_key": (
            data.openai_key
            if data.openai_key and data.openai_key != "***"
            else existing.get("openai_key")
        ),
        "gemini_key": (
            data.gemini_key
            if data.gemini_key and data.gemini_key != "***"
            else existing.get("gemini_key")
        ),
        "perplexity_key": (
            data.perplexity_key
            if data.perplexity_key and data.perplexity_key != "***"
            else existing.get("perplexity_key")
        ),
    }
    doc_ref.set(payload)
    return {"saved": True}
