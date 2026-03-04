# app/services/knowledge_service.py
import aiofiles
import os
from pathlib import Path
from fastapi import UploadFile, HTTPException
from app.config import settings

ALLOWED = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain":    ".txt",
    "text/markdown": ".md",
}
MAX_BYTES = 10 * 1024 * 1024  # 10MB


def _detect_mime(contents: bytes, filename: str) -> str:
    """Simple MIME detection by file extension (avoids python-magic C dependency issues on Render)."""
    ext = Path(filename).suffix.lower()
    ext_map = {
        ".pdf":  "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt":  "text/plain",
        ".md":   "text/markdown",
    }
    return ext_map.get(ext, "application/octet-stream")


async def save_and_extract(file: UploadFile, kb_id: int) -> dict:
    contents = await file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(413, "File exceeds 10MB")

    mime = _detect_mime(contents, file.filename)
    if mime not in ALLOWED:
        raise HTTPException(415, f"Unsupported file type: {mime}. Allowed: PDF, DOCX, TXT, MD")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    path = upload_dir / f"kb_{kb_id}_{file.filename}"

    async with aiofiles.open(path, "wb") as f:
        await f.write(contents)

    text = _extract_text(str(path), mime, contents)
    return {"path": str(path), "mime": mime, "text": text, "size": len(contents)}


def _extract_text(path: str, mime: str, raw: bytes) -> str:
    if mime == "application/pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(path)
            return " ".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            return f"[PDF extraction error: {e}]"
    elif "wordprocessingml" in mime:
        try:
            from docx import Document as DocxDoc
            doc = DocxDoc(path)
            return " ".join(para.text for para in doc.paragraphs)
        except Exception as e:
            return f"[DOCX extraction error: {e}]"
    # Plain text / markdown
    return raw.decode("utf-8", errors="ignore")
