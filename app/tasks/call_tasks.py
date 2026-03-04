# app/tasks/call_tasks.py
import asyncio
import logging
from app.celery_app import celery_app
from app.services.twilio_service import place_outbound_call

log = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def execute_call_task(self, call_id: int, phone_number: str, from_number: str):
    try:
        sid = place_outbound_call(to=phone_number, from_=from_number)
        asyncio.run(_update_call(call_id, sid))
        return {"call_id": call_id, "sid": sid, "status": "placed"}
    except Exception as exc:
        log.error(f"Call task failed for {call_id}: {exc}")
        asyncio.run(_mark_failed(call_id))
        raise self.retry(exc=exc)


async def _update_call(call_id: int, sid: str):
    from app.database import AsyncSessionLocal
    from app.models import Call
    from datetime import datetime, timezone

    async with AsyncSessionLocal() as db:
        call = await db.get(Call, call_id)
        if call:
            call.twilio_sid = sid
            call.status     = "placed"
            call.started_at = datetime.now(timezone.utc)
            call.attempts  += 1
            await db.commit()


async def _mark_failed(call_id: int):
    from app.database import AsyncSessionLocal
    from app.models import Call

    async with AsyncSessionLocal() as db:
        call = await db.get(Call, call_id)
        if call:
            call.status = "failed"
            await db.commit()
