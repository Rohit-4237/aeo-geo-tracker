import csv
import io

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from firebase_db import get_db
from datetime import datetime, timezone

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("/")
def list_prompts():
    db = get_db()
    docs = db.collection("prompts").order_by("order_index").stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]


@router.post("/upload")
async def upload_prompts(file: UploadFile = File(...)):
    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise HTTPException(400, "CSV is empty")

    headers = [h.strip().lower() for h in (reader.fieldnames or [])]
    if "prompt" not in headers:
        raise HTTPException(400, "CSV must have a 'prompt' column")

    db = get_db()
    col = db.collection("prompts")
    # Clear existing prompts
    for doc in col.stream():
        doc.reference.delete()

    saved = 0
    now = datetime.now(timezone.utc).isoformat()
    for i, row in enumerate(rows):
        text_val = row.get("prompt", row.get("Prompt", "")).strip()
        if not text_val:
            continue
        category = row.get("category", row.get("Category", "")).strip() or None
        col.add({"text": text_val, "category": category, "order_index": i, "created_at": now})
        saved += 1

    return {"saved": saved}


@router.delete("/")
def clear_prompts():
    db = get_db()
    for doc in db.collection("prompts").stream():
        doc.reference.delete()
    return {"cleared": True}


@router.get("/template")
def download_template():
    content = (
        "prompt,category\n"
        '"What is the best CRM software for small businesses?",CRM\n'
        '"Which brand offers the best customer support?",Support\n'
    )
    return StreamingResponse(
        io.StringIO(content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=prompts_template.csv"},
    )
