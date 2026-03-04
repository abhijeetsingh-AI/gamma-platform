# app/routers/monitor.py
import time
import asyncio
import psutil
import logging

import google.generativeai as genai
from fastapi import APIRouter
from sqlalchemy import text

from app.database import AsyncSessionLocal
from app.config import settings

router = APIRouter()
log    = logging.getLogger(__name__)


@router.get("/health")
async def health():
    return {"status": "ok", "timestamp": time.time()}


@router.get("/status")
async def full_status():
    results = await asyncio.gather(
        check_database(),
        check_gemini(),
        check_deepgram(),
        check_celery(),
        return_exceptions=True,
    )
    keys = ["database", "gemini", "deepgram", "celery"]
    statuses = {}
    for k, r in zip(keys, results):
        statuses[k] = r if isinstance(r, dict) else {"status": "error", "error": str(r)}

    return {**statuses, "system": get_system(), "tts_provider": settings.tts_provider}


async def check_database() -> dict:
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("PRAGMA integrity_check"))
        return {"status": "ok", "engine": "sqlite+aiosqlite"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def check_gemini() -> dict:
    start = time.time()
    try:
        genai.configure(api_key=settings.gemini_api_key)
        genai.GenerativeModel("gemini-1.5-flash").generate_content("ping")
        ms = round((time.time() - start) * 1000)
        return {"status": "ok" if ms < 3000 else "slow", "latency_ms": ms}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def check_deepgram() -> dict:
    try:
        from deepgram import DeepgramClient
        client   = DeepgramClient(settings.deepgram_api_key)
        projects = client.manage.v("1").get_projects()
        return {"status": "ok", "projects": len(projects.projects)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def check_celery() -> dict:
    try:
        from app.celery_app import celery_app
        workers = celery_app.control.inspect(timeout=2.0).active()
        return {
            "status":       "ok" if workers else "no_workers",
            "worker_count": len(workers) if workers else 0,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_system() -> dict:
    return {
        "cpu_percent":    psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent":   psutil.disk_usage("/").percent,
    }
