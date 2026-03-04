# app/routers/voice.py
import json
import base64
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream

from app.database import get_db
from app.models import Call, Agent
from app.services.voice_pipeline import VoicePipeline
from app.services.tts_service import get_twilio_voice
from app.config import settings
from sqlalchemy import select

router = APIRouter()
log    = logging.getLogger(__name__)

# In-memory map of call_sid → VoicePipeline (one per active call)
active_pipelines: dict[str, VoicePipeline] = {}


# ── Step 1: Twilio hits this when a call arrives ──────────────────────────
@router.post("/incoming")
async def incoming_call(request: Request, db: AsyncSession = Depends(get_db)):
    form        = await request.form()
    from_number = form.get("From", "")
    call_sid    = form.get("CallSid", "")
    log.info(f"Incoming call {call_sid} from {from_number}")

    # Log call to DB
    call = Call(
        phone_number=from_number,
        twilio_sid=call_sid,
        status="active",
        direction="inbound",
    )
    db.add(call)
    await db.commit()

    # Tell Twilio to open a Media Stream to our WebSocket
    response = VoiceResponse()
    connect  = Connect()
    stream   = Stream(url=f"wss://{settings.base_url}/api/voice/stream/{call_sid}")
    connect.append(stream)
    response.append(connect)

    return Response(content=str(response), media_type="application/xml")


# ── Step 2: WebSocket receives raw mulaw audio from Twilio ────────────────
@router.websocket("/stream/{call_sid}")
async def audio_stream(websocket: WebSocket, call_sid: str):
    await websocket.accept()
    log.info(f"WebSocket opened for {call_sid}")

    # Load first active agent's prompt (fallback to default)
    agent_prompt = "You are a friendly AI assistant for Gamma platform."
    gender       = "female"

    pipeline = VoicePipeline(
        call_sid=call_sid,
        websocket=websocket,
        agent_prompt=agent_prompt,
        gender=gender,
    )
    active_pipelines[call_sid] = pipeline
    await pipeline.start()

    try:
        async for message in websocket.iter_text():
            data  = json.loads(message)
            event = data.get("event")

            if event == "start":
                stream_sid = data["start"]["streamSid"]
                await pipeline.on_stream_start(stream_sid)

            elif event == "media":
                audio_bytes = base64.b64decode(data["media"]["payload"])
                await pipeline.on_audio(audio_bytes)

            elif event == "stop":
                await pipeline.on_call_end()
                break

    except WebSocketDisconnect:
        log.info(f"WebSocket disconnected: {call_sid}")
    except Exception as e:
        log.error(f"WebSocket error for {call_sid}: {e}")
    finally:
        await pipeline.cleanup()
        active_pipelines.pop(call_sid, None)


# ── Step 3: Gather endpoint — receives caller speech after <Say> ──────────
# Used in Twilio Say mode (TTS_PROVIDER=twilio)
@router.post("/gather/{call_sid}")
async def gather_response(call_sid: str, request: Request):
    form           = await request.form()
    speech_result  = form.get("SpeechResult", "")
    log.info(f"Gather [{call_sid}]: '{speech_result}'")

    pipeline = active_pipelines.get(call_sid)
    if pipeline and speech_result:
        # Feed transcript directly to LLM (bypasses Deepgram for Gather mode)
        import asyncio
        asyncio.create_task(pipeline._on_transcript(speech_result))

    # Return empty TwiML — pipeline will update the call with new Say
    response = VoiceResponse()
    return Response(content=str(response), media_type="application/xml")


# ── Outbound call trigger (for testing + campaigns) ───────────────────────
@router.post("/call")
async def trigger_call(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    to   = body.get("to")
    if not to:
        return {"error": "to field required"}

    from app.services.twilio_service import place_outbound_call
    sid = place_outbound_call(to=to)

    call = Call(phone_number=to, twilio_sid=sid, status="placed", direction="outbound")
    db.add(call)
    await db.commit()

    return {"sid": sid, "to": to, "status": "placed"}


# ── Status callback from Twilio (update call record) ─────────────────────
@router.post("/status")
async def call_status(request: Request, db: AsyncSession = Depends(get_db)):
    form     = await request.form()
    call_sid = form.get("CallSid", "")
    status   = form.get("CallStatus", "")
    duration = form.get("CallDuration", "0")

    result = await db.execute(select(Call).where(Call.twilio_sid == call_sid))
    call   = result.scalar_one_or_none()
    if call:
        call.status   = status
        call.duration = float(duration)
        await db.commit()

    log.info(f"Status callback: {call_sid} → {status} ({duration}s)")
    return Response(content="", status_code=204)
