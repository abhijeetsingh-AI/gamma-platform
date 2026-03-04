# app/routers/campaigns.py
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models import Campaign, Call, CampaignStatus
from app.services.campaign_service import parse_csv

router = APIRouter()


class CampaignCreate(BaseModel):
    name:             str
    agent_id:         int
    calling_numbers:  list[str] = []
    calling_days:     list[str] = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    timezone:         str       = "UTC"
    start_time:       str       = "09:00"
    end_time:         str       = "17:00"
    max_attempts:     int       = 3
    time_gap_minutes: int       = 30
    allow_callback:   bool      = False
    enable_dnc:       bool      = False


@router.get("/")
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).order_by(Campaign.created_at.desc()))
    campaigns = result.scalars().all()
    return [
        {
            "id": c.id, "name": c.name, "status": c.status.value,
            "agent_id": c.agent_id, "timezone": c.timezone,
        }
        for c in campaigns
    ]


@router.post("/")
async def create_campaign(body: CampaignCreate, db: AsyncSession = Depends(get_db)):
    campaign = Campaign(
        name             = body.name,
        agent_id         = body.agent_id,
        calling_numbers  = json.dumps(body.calling_numbers),
        calling_days     = json.dumps(body.calling_days),
        timezone         = body.timezone,
        start_time       = body.start_time,
        end_time         = body.end_time,
        max_attempts     = body.max_attempts,
        time_gap_minutes = body.time_gap_minutes,
        allow_callback   = body.allow_callback,
        enable_dnc       = body.enable_dnc,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return {"id": campaign.id, "name": campaign.name, "status": "created"}


@router.post("/{campaign_id}/upload-csv")
async def upload_csv(
    campaign_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")

    contacts = await parse_csv(file)

    # Create a Call record for each contact
    created = 0
    for contact in contacts:
        call = Call(
            campaign_id  = campaign_id,
            phone_number = contact["phone_number"],
            status       = "pending",
            direction    = "outbound",
        )
        db.add(call)
        created += 1

    await db.commit()
    return {"contacts_imported": created, "campaign_id": campaign_id}


@router.post("/{campaign_id}/start")
async def start_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    if campaign.status == CampaignStatus.RUNNING:
        raise HTTPException(400, "Campaign already running")

    from app.scheduler import schedule_campaign
    schedule_campaign({
        "id":           campaign.id,
        "calling_days": json.loads(campaign.calling_days),
        "start_time":   campaign.start_time,
        "timezone":     campaign.timezone,
    })
    campaign.status = CampaignStatus.RUNNING
    await db.commit()
    return {"status": "scheduled", "campaign_id": campaign_id}


@router.post("/{campaign_id}/stop")
async def stop_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    campaign.status = CampaignStatus.FROZEN
    await db.commit()

    from app.scheduler import scheduler
    try:
        scheduler.remove_job(f"campaign_{campaign_id}")
    except Exception:
        pass
    return {"status": "stopped", "campaign_id": campaign_id}
