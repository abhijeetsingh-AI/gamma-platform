# app/scheduler.py
import pytz
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

log       = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

DAY_MAP = {
    "Mon": "mon", "Tue": "tue", "Wed": "wed",
    "Thu": "thu", "Fri": "fri", "Sat": "sat", "Sun": "sun",
}


def schedule_campaign(campaign: dict):
    days = ",".join(DAY_MAP[d] for d in campaign["calling_days"] if d in DAY_MAP)
    tz   = pytz.timezone(campaign["timezone"])
    h, m = campaign["start_time"].split(":")

    scheduler.add_job(
        run_campaign_batch,
        trigger         = CronTrigger(day_of_week=days, hour=int(h), minute=int(m), timezone=tz),
        args            = [campaign["id"]],
        id              = f"campaign_{campaign['id']}",
        replace_existing= True,
        misfire_grace_time = 300,
    )
    log.info(f"Scheduled campaign {campaign['id']} at {h}:{m} {tz}")


async def run_campaign_batch(campaign_id: int):
    from app.database import AsyncSessionLocal
    from app.models import Call, Campaign, CampaignStatus
    from sqlalchemy import select
    from app.tasks.call_tasks import execute_call_task
    from app.config import settings

    async with AsyncSessionLocal() as db:
        campaign = await db.get(Campaign, campaign_id)
        if not campaign or campaign.status not in (CampaignStatus.RUNNING, CampaignStatus.FROZEN):
            return

        result = await db.execute(
            select(Call).where(
                Call.campaign_id == campaign_id,
                Call.status      == "pending",
                Call.attempts    < campaign.max_attempts,
            ).limit(50)
        )
        calls = result.scalars().all()

        for i, call in enumerate(calls):
            execute_call_task.apply_async(
                args      = [call.id, call.phone_number, settings.twilio_phone_number],
                countdown = campaign.time_gap_minutes * 60 * i,
            )

        log.info(f"Dispatched {len(calls)} calls for campaign {campaign_id}")
