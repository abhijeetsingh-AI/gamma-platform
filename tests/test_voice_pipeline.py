# tests/test_voice_pipeline.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_gemini_responds_with_json():
    from app.services.llm_service import GeminiConversation

    mock_response      = MagicMock()
    mock_response.text = '{"speak":"Hello!","intent":"greeting","next_action":"continue","sentiment":"positive"}'

    with patch("google.generativeai.GenerativeModel") as MockModel:
        mock_chat                     = MagicMock()
        mock_chat.send_message        = MagicMock(return_value=mock_response)
        MockModel.return_value.start_chat = MagicMock(return_value=mock_chat)

        conv   = GeminiConversation("Test prompt")
        result = await conv.respond("Hello")

        assert result["speak"]       == "Hello!"
        assert result["next_action"] == "continue"
        assert result["intent"]      == "greeting"


@pytest.mark.asyncio
async def test_gemini_fallback_on_bad_json():
    from app.services.llm_service import GeminiConversation

    mock_response      = MagicMock()
    mock_response.text = "not valid json at all"

    with patch("google.generativeai.GenerativeModel") as MockModel:
        mock_chat              = MagicMock()
        mock_chat.send_message = MagicMock(return_value=mock_response)
        MockModel.return_value.start_chat = MagicMock(return_value=mock_chat)

        conv   = GeminiConversation("Test prompt")
        result = await conv.respond("Hello")

        assert result["next_action"] == "continue"
        assert result["intent"]      == "fallback"


@pytest.mark.asyncio
async def test_tts_twilio_mode_returns_none():
    """In Twilio Say mode, synthesize_speech returns None (TwiML handles audio)."""
    with patch("app.services.tts_service.settings") as mock_settings:
        mock_settings.tts_provider = "twilio"
        from app.services.tts_service import synthesize_speech
        result = await synthesize_speech("Hello world", "female", "mulaw")
        assert result is None


def test_campaign_csv_validation():
    """CSV parser rejects invalid phone numbers."""
    import asyncio
    import io
    from unittest.mock import AsyncMock
    from fastapi import UploadFile
    from app.services.campaign_service import parse_csv

    csv_content = b"phone_number\n+12025551234\n+447911123456\n"
    mock_file   = AsyncMock(spec=UploadFile)
    mock_file.read.return_value = csv_content

    result = asyncio.run(parse_csv(mock_file))
    assert len(result) == 2
    assert result[0]["phone_number"] == "+12025551234"
