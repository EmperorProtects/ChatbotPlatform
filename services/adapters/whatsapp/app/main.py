from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from typing import Optional, Dict, Any
from pydantic import BaseModel
import logging
import httpx
import os

app = FastAPI(title="Whatsapp Adapter", version="1.0.0")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("whatsapp_adapter")

WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL", "https://graph.facebook.com/")
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://api_gateway:8000")
APP_SECRET= os.getenv("APP_SECRET", "")
    
WHATSAPP_PHONE_NUMBER = "15551488970"
GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v23.0")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")  # <TEST_BUSINESS_PHONE_NUMBER_ID>
SYSTEM_USER_ACCESS_TOKEN = os.getenv("SYSTEM_USER_ACCESS_TOKEN")  # <SYSTEM_USER_ACCESS_TOKEN>

DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=10.0)
class WhatsAppAPIError(Exception):
    def __init__(self, status_code: int, data: dict):
        self.status_code = status_code
        self.data = data
        super().__init__(f"WhatsApp API error {status_code}: {data}")

async def send_message_to_whatsapp(
    message: str,
    number: str,
    *,
    phone_number_id: Optional[str] = None,
    access_token: Optional[str] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> Dict[str, Any]:
    """
    Отправка text сообщения через WhatsApp Cloud API.
    Возвращает: {"status": "...", "message_id": "...", "raw": {...}}
    """
    if not message or not message.strip():
       # raise ValueError("message is empty")
       logger.info("message from closed chat")
       return {"satus": 200}

    phone_number_id = phone_number_id or WHATSAPP_PHONE_NUMBER_ID
    access_token = access_token or SYSTEM_USER_ACCESS_TOKEN

    if not phone_number_id:
        raise ValueError("WHATSAPP_PHONE_NUMBER_ID is not set")
    if not access_token:
        raise ValueError("SYSTEM_USER_ACCESS_TOKEN is not set")
    def normalize_digits(phone: str)-> str:
        if phone.startswith("7") and len(phone) == 11:
            return "7" + "8" + phone[1:]
        return phone
    
    to_number = normalize_digits(number)
    logger.info(f"Sending to {to_number}")

    url =  WHATSAPP_API_URL + f"{GRAPH_API_VERSION}/{phone_number_id}/messages"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        #"to": "787785862952",
        #"to": "877785862952",
        "type": "text",
        "text": {"body": message},
    }

    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)
        close_client = True

    try:
        resp = await client.post(url, headers=headers, json=payload)

        # WhatsApp Cloud API обычно возвращает JSON; при ошибке тоже JSON с "error"
        try:
            data = resp.json()
        except Exception:
            data = {"raw_text": resp.text}

        if resp.status_code >= 400:
            raise WhatsAppAPIError(resp.status_code, data)

        # Пример успешного ответа содержит messages: [{"id": "..."}]
        message_id = None
        if isinstance(data, dict):
            msgs = data.get("messages")
            if isinstance(msgs, list) and msgs:
                message_id = msgs[0].get("id")

        return {
            "status": "success",
            "to": to_number,
            "message_id": message_id,
            "raw": data,
        }
    finally:
        if close_client:
            await client.aclose()



def verify_signature(raw_body: bytes, signature_header: str | None):
    # Meta: "X-Hub-Signature-256: sha256=..."
    if not APP_SECRET:
        return
    if not signature_header or not signature_header.startswith("sha256="):
        raise HTTPException(401, "Missing signature")
    sent = signature_header.split("sha256=", 1)[1]
    expected = hmac.new(APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sent, expected):
        raise HTTPException(401, "Bad signature")

async def call_api(phone_number: str, text: str):
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(url=API_GATEWAY_URL + "/bot/incoming", json={
                "user_id": phone_number,  # Используем номер телефона как user_id
                "brief_id": 1,  
                "text": text,
                "channel": "whatsapp",
                "language": "ru"
            })
                        
            if r.status_code == 200:
                message = r.json().get("text", "")
            else:
                message = "Извините, произошла ошибка при обработке вашего сообщения."
    except Exception as e:
        logger.error(f"Error forwarding message to API Gateway: {e}")
        raise HTTPException(500, "Failed to process message")
    if message is None:
        return
    await send_message_to_whatsapp(message,phone_number)

@app.get("/webhook/")
@app.get("/webhook")
async def whatsapp_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    challenge = params.get("hub.challenge")
    token = params.get("hub.verify_token")
    if mode == "subscribe" and token == os.getenv("WHATSAPP_TOKEN"):
        logger.info("Webhook verified successfully.")
        # return int(challenge)
        return PlainTextResponse(content=challenge, status_code=200)
    raise HTTPException(status_code=403)

@app.post("/webhook/")
@app.post("/webhook")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    raw = await request.body()
    verify_signature(raw, request.headers.get("X-Hub-Signature-256"))
    payload = await request.json()
    
    value = payload.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})
    #phone_number_id = value.get("metadata", {}).get("phone_number_id")

    

   # if phone_number_id == WHATSAPP_PHONE_NUMBER_ID:
    #    logger.info(f"Received self-message ")
    #    return PlainTextResponse(content="OK", status_code=200)

    msg = value.get("messages", [{}])
    logger.info(msg)
    if msg == [{}]:
        logger.info(f"Received self-message ")
        return PlainTextResponse(content="OK", status_code=200)
    msg = msg[0]
    phone_number = msg.get("from")

    text = msg.get("text", {}).get("body", "")
    # user_id = value.get("messages", [{}])[0].get("from")

    # user_id = valeu.get("messages", {}).get("from")
    background_tasks.add_task(call_api, phone_number, text)
    return {"status": 200}

@app.get("/")
async def root():
    return {"message": "Whatsapp Adapter", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}


