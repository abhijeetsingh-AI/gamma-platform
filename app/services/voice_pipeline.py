# app/services/voice_pipeline.py
"""
VoicePipeline orchestrates the full AI voice conversation:
  Twilio Audio → Deepgram STT → Gemini LLM → TTS → back to Twilio

Two TTS modes:
  TTS_PROVIDER=twilio  → Sends TwiML <Say> redirect after each response (no raw audio streaming)
  TTS_PROVIDER=google  → Streams raw mulaw audio bytes over WebSocket
"""
import asyncio
import base64
import json
import logging

from fastapi import WebSocket
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import VoiceResponse, Gather

from app.config import settings
from app.services.stt_service import DeepgramSTT
from app.services.llm_service import GeminiConversation
from app.services.tts_service import synthesize_speech, get_twilio_voice

log = logging.getLogger(__name__)


class VoicePipeline:
    def __init__(
        self,
        call_sid: str,
        websocket: WebSocket,
        agent_prompt: str = "You are a friendly AI sales agent for Gamma.",
        gender: str = "female",
    ):
        self.call_sid   = call_sid
        self.ws         = websocket
        self.stream_sid = None
        self.gender     = gender
        self.transcript = []
        self._processing = False  # prevent overlapping LLM calls

        self.stt = DeepgramSTT(on_transcript_callback=self._on_transcript)
        self.llm = GeminiConversation(agent_prompt=agent_prompt, gender=gender)

    async def start(self):
        await self.stt.connect()
        log.info(f"Pipeline started for {self.call_sid}")

    async def on_stream_start(self, stream_sid: str):
        self.stream_sid = stream_sid
        log.info(f"Stream started: {stream_sid}")
        # Greet the caller
        await self._respond_to_caller("Hello! Thank you for calling. How can I help you today?")

    async def on_audio(self, audio_bytes: bytes):
        await self.stt.send_audio(audio_bytes)

    async def _on_transcript(self, text: str):
        """Called by Deepgram when a final transcript is ready."""
        if self._processing:
            log.info("Still processing previous turn, dropping transcript")
            return

        self._processing = True
        try:
            log.info(f"Caller said: {text}")
            self.transcript.append({"role": "caller", "text": text})

            llm_result  = await self.llm.respond(text)
            speak_text  = llm_result["speak"]
            next_action = llm_result["next_action"]

            self.transcript.append({"role": "agent", "text": speak_text})

            await self._respond_to_caller(speak_text)

            if next_action == "end_call":
                await asyncio.sleep(2)
                await self._hangup()
            elif next_action == "transfer_to_human":
                await self._respond_to_caller("Please hold while I transfer you to a team member.")
                await asyncio.sleep(1)
                await self._transfer(settings.twilio_phone_number)

        except Exception as e:
            log.error(f"Pipeline error in _on_transcript: {e}")
        finally:
            self._processing = False

    async def _respond_to_caller(self, text: str):
        """Send TTS response back to the caller."""
        if settings.tts_provider == "google":
            await self._speak_google(text)
        else:
            await self._speak_twilio(text)

    async def _speak_twilio(self, text: str):
        """
        Twilio Say mode: update the live call with new TwiML containing <Say>.
        This is the default — no GCP credentials needed.
        """
        try:
            client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
            response = VoiceResponse()
            # <Gather> listens for caller input after speaking
            gather = Gather(
                input="speech",
                action=f"https://{settings.base_url}/api/voice/gather/{self.call_sid}",
                method="POST",
                speech_timeout="auto",
                language="en-US",
            )
            gather.say(text, voice=get_twilio_voice(self.gender))
            response.append(gather)
            # Fallback if no input
            response.say("Are you still there?", voice=get_twilio_voice(self.gender))

            client.calls(self.call_sid).update(twiml=str(response))
            log.info(f"Twilio Say: {text[:60]}")
        except Exception as e:
            log.error(f"Twilio Say error: {e}")

    async def _speak_google(self, text: str):
        """
        Google TTS mode: synthesize to mulaw bytes and stream directly over WebSocket.
        Activate with TTS_PROVIDER=google in .env.
        """
        if not self.stream_sid:
            return
        try:
            audio_bytes = await synthesize_speech(text, self.gender, "mulaw")
            if audio_bytes:
                audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                await self.ws.send_text(json.dumps({
                    "event":     "media",
                    "streamSid": self.stream_sid,
                    "media":     {"payload": audio_b64},
                }))
                log.info(f"Google TTS streamed: {text[:60]}")
        except Exception as e:
            log.error(f"Google TTS stream error: {e}")

    async def _hangup(self):
        try:
            client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
            response = VoiceResponse()
            response.say("Thank you for calling. Goodbye!", voice=get_twilio_voice(self.gender))
            response.hangup()
            client.calls(self.call_sid).update(twiml=str(response))
        except Exception as e:
            log.error(f"Hangup error: {e}")

    async def _transfer(self, to_number: str):
        try:
            client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
            response = VoiceResponse()
            response.dial(to_number)
            client.calls(self.call_sid).update(twiml=str(response))
        except Exception as e:
            log.error(f"Transfer error: {e}")

    async def on_call_end(self):
        await self.stt.finish()
        log.info(f"Call ended. Transcript lines: {len(self.transcript)}")

    async def cleanup(self):
        try:
            await self.stt.finish()
        except Exception:
            pass
