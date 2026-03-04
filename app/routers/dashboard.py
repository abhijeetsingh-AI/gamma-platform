# app/routers/dashboard.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.database import get_db
from app.models import Call, Campaign, CampaignStatus

router = APIRouter()


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)):
    total_calls = (await db.execute(select(func.count()).select_from(Call))).scalar() or 0
    total_secs  = (await db.execute(select(func.sum(Call.duration)))).scalar() or 0
    total_min   = round(total_secs / 60, 2)

    concurrency = (await db.execute(
        select(func.count()).select_from(Call).where(
            and_(Call.started_at.isnot(None), Call.ended_at.is_(None))
        )
    )).scalar() or 0

    statuses = await db.execute(
        select(Campaign.status, func.count(Campaign.id).label("n")).group_by(Campaign.status)
    )
    status_map = {r.status.value: r.n for r in statuses}

    chart = await db.execute(
        select(func.date(Call.started_at).label("d"), func.count(Call.id).label("c"))
        .group_by("d").order_by("d").limit(30)
    )

    return {
        "total_calls":     total_calls,
        "total_minutes":   total_min,
        "concurrency":     concurrency,
        "campaign_status": status_map,
        "calls_chart":     [{"date": r.d, "count": r.c} for r in chart],
    }
