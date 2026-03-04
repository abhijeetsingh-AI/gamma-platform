# app/routers/phone.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.models import PhoneNumber
from app.services.twilio_service import verify_credentials

router = APIRouter()


class VerifyRequest(BaseModel):
    account_sid:  str
    auth_token:   str
    phone_number: str


@router.post("/verify")
async def verify_phone(body: VerifyRequest, db: AsyncSession = Depends(get_db)):
    result = await verify_credentials(body.account_sid, body.auth_token, body.phone_number)
    if result["verified"]:
        from datetime import datetime, timezone
        phone = PhoneNumber(
            provider     = "twilio",
            phone_number = body.phone_number,
            verified     = True,
            verified_at  = datetime.now(timezone.utc),
        )
        db.add(phone)
        await db.commit()
    return result


@router.get("/numbers")
async def list_numbers(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(select(PhoneNumber))
    numbers = result.scalars().all()
    return [{"id": n.id, "provider": n.provider, "number": n.phone_number, "verified": n.verified} for n in numbers]
