# app/services/stt_service.py
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
from app.config import settings
import logging

log = logging.getLogger(__name__)


class DeepgramSTT:
    """Manages a single Deepgram live WebSocket connection per call."""

    def __init__(self, on_transcript_callback):
        self.client         = DeepgramClient(settings.deepgram_api_key)
        self.connection     = None
        self.on_transcript  = on_transcript_callback

    async def connect(self):
        self.connection = self.client.listen.asynclive.v("1")

        self.connection.on(LiveTranscriptionEvents.Transcript, self._on_transcript)
        self.connection.on(LiveTranscriptionEvents.Error,      self._on_error)
        self.connection.on(LiveTranscriptionEvents.Close,      self._on_close)

        options = LiveOptions(
            model           = settings.deepgram_model,  # nova-2-phonecall
            language        = "en-US",
            encoding        = "mulaw",
            sample_rate     = 8000,
            channels        = 1,
            punctuate       = True,
            interim_results = False,
            endpointing     = 300,
            utterance_end_ms= "1000",
        )
        await self.connection.start(options)
        log.info("Deepgram STT connected")

    async def send_audio(self, audio_chunk: bytes):
        if self.connection:
            await self.connection.send(audio_chunk)

    async def finish(self):
        if self.connection:
            try:
                await self.connection.finish()
            except Exception as e:
                log.warning(f"Deepgram finish error (safe to ignore): {e}")

    async def _on_transcript(self, *args, **kwargs):
        result = kwargs.get("result")
        if not result:
            return
        sentence = result.channel.alternatives[0].transcript
        is_final  = result.is_final
        if is_final and sentence.strip():
            log.info(f"STT final: {sentence}")
            await self.on_transcript(sentence)

    async def _on_error(self, *args, **kwargs):
        log.error(f"Deepgram error: {kwargs}")

    async def _on_close(self, *args, **kwargs):
        log.info("Deepgram connection closed")
