# app/models.py
import enum
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class CampaignStatus(enum.Enum):
    FROZEN    = "frozen"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"


class AgentType(enum.Enum):
    VOICE         = "voice"
    WHATSAPP      = "whatsapp"
    VOICE_BLASTER = "voice_blaster"


class Agent(Base):
    __tablename__ = "agents"
    id:         Mapped[int]       = mapped_column(Integer, primary_key=True, index=True)
    name:       Mapped[str]       = mapped_column(String(255))
    type:       Mapped[AgentType] = mapped_column(Enum(AgentType), default=AgentType.VOICE)
    gender:     Mapped[str]       = mapped_column(String(10), default="female")
    prompt:     Mapped[str]       = mapped_column(Text)
    created_at                    = mapped_column(DateTime, server_default=func.now())


class Campaign(Base):
    __tablename__ = "campaigns"
    id:               Mapped[int]            = mapped_column(Integer, primary_key=True, index=True)
    name:             Mapped[str]            = mapped_column(String(255))
    type:             Mapped[str]            = mapped_column(String(50), default="outbound")
    agent_id:         Mapped[int]            = mapped_column(ForeignKey("agents.id"))
    status:           Mapped[CampaignStatus] = mapped_column(Enum(CampaignStatus), default=CampaignStatus.FROZEN)
    calling_numbers:  Mapped[str]            = mapped_column(Text, default="[]")
    allow_callback:   Mapped[bool]           = mapped_column(Boolean, default=False)
    enable_dnc:       Mapped[bool]           = mapped_column(Boolean, default=False)
    calling_days:     Mapped[str]            = mapped_column(Text, default='["Mon","Tue","Wed","Thu","Fri"]')
    timezone:         Mapped[str]            = mapped_column(String(100), default="UTC")
    start_time:       Mapped[str]            = mapped_column(String(8), default="09:00")
    end_time:         Mapped[str]            = mapped_column(String(8), default="17:00")
    max_attempts:     Mapped[int]            = mapped_column(Integer, default=3)
    time_gap_minutes: Mapped[int]            = mapped_column(Integer, default=30)
    created_at                               = mapped_column(DateTime, server_default=func.now())
    calls: Mapped[list["Call"]]              = relationship("Call", back_populates="campaign")


class Call(Base):
    __tablename__ = "calls"
    id:           Mapped[int]   = mapped_column(Integer, primary_key=True, index=True)
    campaign_id:  Mapped[int]   = mapped_column(ForeignKey("campaigns.id"), nullable=True)
    phone_number: Mapped[str]   = mapped_column(String(30))
    status:       Mapped[str]   = mapped_column(String(50), default="pending")
    direction:    Mapped[str]   = mapped_column(String(20), default="inbound")
    twilio_sid:   Mapped[str]   = mapped_column(String(100), nullable=True)
    duration:     Mapped[float] = mapped_column(Float, default=0.0)
    attempts:     Mapped[int]   = mapped_column(Integer, default=0)
    started_at                  = mapped_column(DateTime, nullable=True)
    ended_at                    = mapped_column(DateTime, nullable=True)
    transcript:   Mapped[str]   = mapped_column(Text, nullable=True)
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="calls")


class PhoneNumber(Base):
    __tablename__ = "phone_numbers"
    id:           Mapped[int]  = mapped_column(Integer, primary_key=True)
    provider:     Mapped[str]  = mapped_column(String(50), default="twilio")
    phone_number: Mapped[str]  = mapped_column(String(30))
    verified:     Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at                = mapped_column(DateTime, nullable=True)


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"
    id:             Mapped[int] = mapped_column(Integer, primary_key=True)
    filename:       Mapped[str] = mapped_column(String(255))
    file_path:      Mapped[str] = mapped_column(Text, nullable=True)
    mime_type:      Mapped[str] = mapped_column(String(100), nullable=True)
    size_bytes:     Mapped[int] = mapped_column(Integer, nullable=True)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=True)
    status:         Mapped[str] = mapped_column(String(30), default="pending")
    created_at                  = mapped_column(DateTime, server_default=func.now())
    processed_at                = mapped_column(DateTime, nullable=True)


class Integration(Base):
    __tablename__ = "integrations"
    id:            Mapped[int]  = mapped_column(Integer, primary_key=True)
    provider:      Mapped[str]  = mapped_column(String(50), unique=True)
    access_token:  Mapped[str]  = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str]  = mapped_column(Text, nullable=True)
    connected:     Mapped[bool] = mapped_column(Boolean, default=False)
    connected_at               = mapped_column(DateTime, nullable=True)
