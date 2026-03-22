import httpx
import logging
from config import settings

logger = logging.getLogger(__name__)

BASE = f"{settings.GREEN_API_BASE_URL}/waInstance{settings.GREEN_API_INSTANCE_ID}"
TOKEN = settings.GREEN_API_TOKEN

async def send_message(phone: str, text: str) -> bool:
    chat_id = f"{phone}@c.us"
    url = f"{BASE}/sendMessage/{TOKEN}"
    payload = {"chatId": chat_id, "message": text}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            logger.info(f"Message sent to {phone}")
            return True
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return False

def parse_incoming(body: dict) -> dict | None:
    try:
        msg_data = body.get("messageData", {})
        msg_type = msg_data.get("typeMessage", "")
        if msg_type not in ("textMessage", "extendedTextMessage"):
            return None
        sender_data = body.get("senderData", {})
        sender = sender_data.get("sender", "")
        sender_phone = sender.replace("@c.us", "")
        if sender_phone != settings.MY_PHONE_NUMBER:
            logger.info(f"Ignoring message from: {sender_phone}")
            return None
        if msg_type == "textMessage":
            text = msg_data.get("textMessageData", {}).get("textMessage", "")
        else:
            text = msg_data.get("extendedTextMessageData", {}).get("text", "")
        if not text:
            return None
        return {"phone": sender_phone, "text": text.strip()}
    except Exception as e:
        logger.error(f"Error parsing webhook: {e}")
        return None
