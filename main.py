# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import init_db
from app.routers import dashboard, agents, campaigns, phone, knowledge, monitor, voice


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    from app.scheduler import scheduler
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Gamma API", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router, prefix="/api/dashboard")
app.include_router(agents.router,    prefix="/api/agents")
app.include_router(campaigns.router, prefix="/api/campaigns")
app.include_router(phone.router,     prefix="/api/phone")
app.include_router(knowledge.router, prefix="/api/knowledge")
app.include_router(monitor.router,   prefix="/api/monitor")
app.include_router(voice.router,     prefix="/api/voice")


@app.get("/")
async def root():
    return {"status": "Gamma API running", "docs": "/docs"}
