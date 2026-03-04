# app/services/twilio_service.py
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from app.config import settings
import logging

log = logging.getLogger(__name__)


def get_client() -> Client:
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


async def verify_credentials(account_sid: str, auth_token: str, phone_number: str) -> dict:
    try:
        client  = Client(account_sid, auth_token)
        account = client.api.accounts(account_sid).fetch()
        numbers = client.incoming_phone_numbers.list(phone_number=phone_number)
        if not numbers:
            raise ValueError(f"Phone {phone_number} not found in account")
        return {"verified": True, "status": account.status}
    except TwilioRestException as e:
        return {"verified": False, "error": str(e)}
    except Exception as e:
        return {"verified": False, "error": str(e)}


def place_outbound_call(to: str, from_: str = None) -> str:
    client = get_client()
    call = client.calls.create(
        to    = to,
        from_ = from_ or settings.twilio_phone_number,
        url   = f"https://{settings.base_url}/api/voice/incoming",
        method= "POST",
    )
    log.info(f"Outbound call placed: {call.sid} → {to}")
    return call.sid
