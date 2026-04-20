from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
import io
import csv
from database import get_db
from models import Prompt

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("/")
async def list_prompts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).order_by(Prompt.order_index))
    return [{"id": p.id, "text": p.text, "category": p.category, "order_index": p.order_index} for p in result.scalars()]


@router.post("/upload")
async def upload_prompts(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    rows = list(reader)
    if not rows:
        raise HTTPException(400, "CSV is empty")

    # Accept columns: 'prompt' (required), 'category' (optional)
    headers = [h.strip().lower() for h in reader.fieldnames or []]
    if "prompt" not in headers:
        raise HTTPException(400, "CSV must have a 'prompt' column")

    await db.execute(delete(Prompt))
    saved = 0
    for i, row in enumerate(rows):
        text_val = row.get("prompt", row.get("Prompt", "")).strip()
        if not text_val:
            continue
        category = row.get("category", row.get("Category", "")).strip() or None
        db.add(Prompt(text=text_val, category=category, order_index=i))
        saved += 1

    await db.commit()
    return {"saved": saved}


@router.delete("/")
async def clear_prompts(db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Prompt))
    await db.commit()
    return {"cleared": True}


@router.get("/template")
async def download_template():
    from fastapi.responses import StreamingResponse
    content = "prompt,category\n\"What is the best CRM software for small businesses?\",CRM\n\"Which brand offers the best customer support?\",Support\n"
    return StreamingResponse(
        io.StringIO(content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=prompts_template.csv"},
    )
