# app/routers/agents.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models import Agent, AgentType

router = APIRouter()


class AgentCreate(BaseModel):
    name:   str
    type:   str = "voice"
    gender: str = "female"
    prompt: str


class AgentUpdate(BaseModel):
    name:   str | None = None
    gender: str | None = None
    prompt: str | None = None


@router.get("/")
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).order_by(Agent.created_at.desc()))
    agents = result.scalars().all()
    return [
        {"id": a.id, "name": a.name, "type": a.type.value, "gender": a.gender, "prompt": a.prompt}
        for a in agents
    ]


@router.post("/")
async def create_agent(body: AgentCreate, db: AsyncSession = Depends(get_db)):
    agent = Agent(
        name   = body.name,
        type   = AgentType(body.type),
        gender = body.gender,
        prompt = body.prompt,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return {"id": agent.id, "name": agent.name, "status": "created"}


@router.get("/{agent_id}")
async def get_agent(agent_id: int, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    return {"id": agent.id, "name": agent.name, "type": agent.type.value,
            "gender": agent.gender, "prompt": agent.prompt}


@router.patch("/{agent_id}")
async def update_agent(agent_id: int, body: AgentUpdate, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    if body.name   is not None: agent.name   = body.name
    if body.gender is not None: agent.gender = body.gender
    if body.prompt is not None: agent.prompt = body.prompt
    await db.commit()
    return {"id": agent.id, "status": "updated"}


@router.delete("/{agent_id}")
async def delete_agent(agent_id: int, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    await db.delete(agent)
    await db.commit()
    return {"status": "deleted"}
