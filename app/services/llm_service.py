# app/services/llm_service.py
import google.generativeai as genai
import json
from app.config import settings
import logging

log = logging.getLogger(__name__)

genai.configure(api_key=settings.gemini_api_key)

VOICE_SYSTEM_PROMPT = """
You are a professional AI voice agent for Gamma platform. You are on a live phone call.
Keep responses SHORT (1-2 sentences max) — this text will be spoken aloud via TTS.
Always respond ONLY with valid JSON in this exact structure:
{
  "speak":       "<exact text to say to caller — short and natural>",
  "intent":      "<greeting|pitch|objection_handle|close|transfer|schedule|end_call>",
  "next_action": "<continue|transfer_to_human|schedule_callback|end_call>",
  "sentiment":   "<positive|neutral|negative>"
}
Rules:
- Never break character
- If caller is angry or asks for human, set next_action to transfer_to_human
- If caller agrees to callback, set next_action to schedule_callback
- Keep speak text under 30 words — it will be read aloud
"""


class GeminiConversation:
    """Maintains conversation history for a single call session."""

    def __init__(self, agent_prompt: str = "You are a friendly AI assistant.", gender: str = "female"):
        self.model = genai.GenerativeModel(
            settings.gemini_model,
            system_instruction=VOICE_SYSTEM_PROMPT + f"\nAgent persona: {agent_prompt}\nGender: {gender}",
        )
        self.chat    = self.model.start_chat(history=[])
        self.gender  = gender
        self.history = []

    async def respond(self, caller_text: str) -> dict:
        try:
            response = self.chat.send_message(
                caller_text,
                generation_config=genai.GenerationConfig(
                    temperature=0.4,
                    max_output_tokens=200,
                    response_mime_type="application/json",
                ),
            )
            result = json.loads(response.text)
            self.history.append({"caller": caller_text, "agent": result["speak"]})
            log.info(f"Gemini intent={result['intent']} action={result['next_action']}")
            return result
        except (json.JSONDecodeError, KeyError) as e:
            log.error(f"Gemini parse error: {e} | raw: {response.text}")
            return {
                "speak":       "Sorry, could you repeat that?",
                "intent":      "fallback",
                "next_action": "continue",
                "sentiment":   "neutral",
            }
        except Exception as e:
            log.error(f"Gemini error: {e}")
            return {
                "speak":       "I apologize, I had a technical issue. Could you repeat that?",
                "intent":      "fallback",
                "next_action": "continue",
                "sentiment":   "neutral",
            }
