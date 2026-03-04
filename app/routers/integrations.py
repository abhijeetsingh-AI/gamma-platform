# app/routers/integrations.py
# HubSpot OAuth — placeholder (add hubspot-api-client when needed)
from fastapi import APIRouter
router = APIRouter()

@router.get("/")
async def list_integrations():
    return {"integrations": ["hubspot"]}

@router.get("/hubspot/status")
async def hubspot_status():
    return {"provider": "hubspot", "connected": False}
