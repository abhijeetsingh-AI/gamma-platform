# app/services/tts_service.py
"""
TTS Provider abstraction.

TTS_PROVIDER=twilio  → Uses Twilio <Say> verb — no GCP needed. Works immediately.
TTS_PROVIDER=google  → Uses Google Cloud Neural2 voices — requires GCP service account.

Switch by setting TTS_PROVIDER in .env once GCP credentials are ready.
"""
import base64
import logging
from app.config import settings

log = logging.getLogger(__name__)

# ── Twilio Say voice map ──────────────────────────────────────────────────────
TWILIO_VOICE_MAP = {
    "female": "Polly.Joanna",   # AWS Polly via Twilio — natural female voice
    "male":   "Polly.Matthew",
}


async def synthesize_speech(text: str, gender: str = "female", audio_format: str = "mulaw") -> bytes | None:
    """
    Returns audio bytes if using Google TTS, or None if using Twilio Say mode.
    In Twilio Say mode, the VoicePipeline generates TwiML instead of sending raw audio.
    """
    if settings.tts_provider == "google":
        return await _google_tts(text, gender, audio_format)
    # Twilio Say mode — caller audio is handled via TwiML, not raw bytes
    return None


async def _google_tts(text: str, gender: str, audio_format: str) -> bytes:
    """Google Cloud Neural2 TTS — activate by setting TTS_PROVIDER=google in .env."""
    try:
        from google.cloud import texttospeech

        client = texttospeech.TextToSpeechClient()
        voice_map = {
            "female": settings.tts_voice_female,
            "male":   settings.tts_voice_male,
        }

        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=settings.tts_language_code,
            name=voice_map.get(gender, voice_map["female"]),
            ssml_gender=(
                texttospeech.SsmlVoiceGender.FEMALE if gender == "female"
                else texttospeech.SsmlVoiceGender.MALE
            ),
        )

        if audio_format == "mulaw":
            audio_config = texttospeech.AudioConfig(
                audio_encoding    = texttospeech.AudioEncoding.MULAW,
                sample_rate_hertz = 8000,
                speaking_rate     = 1.05,
            )
        else:
            audio_config = texttospeech.AudioConfig(
                audio_encoding = texttospeech.AudioEncoding.MP3,
                speaking_rate  = 1.0,
            )

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        log.info(f"Google TTS: {len(text)} chars → {len(response.audio_content)} bytes")
        return response.audio_content

    except Exception as e:
        log.error(f"Google TTS error: {e}")
        raise


def get_twilio_voice(gender: str = "female") -> str:
    """Return Twilio voice name for <Say> verb."""
    return TWILIO_VOICE_MAP.get(gender, TWILIO_VOICE_MAP["female"])
