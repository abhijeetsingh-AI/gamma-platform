# app/routers/knowledge.py
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import KnowledgeBase
from app.services.knowledge_service import save_and_extract
from datetime import datetime, timezone

router = APIRouter()


@router.get("/")
async def list_knowledge(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()))
    files  = result.scalars().all()
    return [
        {"id": f.id, "filename": f.filename, "status": f.status,
         "size_bytes": f.size_bytes, "mime_type": f.mime_type}
        for f in files
    ]


@router.post("/upload")
async def upload_file(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    kb = KnowledgeBase(filename=file.filename, status="processing")
    db.add(kb)
    await db.commit()
    await db.refresh(kb)

    try:
        result = await save_and_extract(file, kb.id)
        kb.file_path      = result["path"]
        kb.mime_type      = result["mime"]
        kb.size_bytes     = result["size"]
        kb.extracted_text = result["text"]
        kb.status         = "ready"
        kb.processed_at   = datetime.now(timezone.utc)
    except Exception as e:
        kb.status = f"error: {str(e)[:100]}"

    await db.commit()
    return {"id": kb.id, "filename": kb.filename, "status": kb.status}
