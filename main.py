import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from config import settings
from database import init_db
from scheduler import start_scheduler, stop_scheduler
from webhook_handler import handle_incoming_message

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting WhatsApp Secretary...")
    await init_db()
    scheduler_task = asyncio.create_task(start_scheduler())
    logger.info("Server ready!")
    yield
    await stop_scheduler()
    scheduler_task.cancel()

app = FastAPI(title="WhatsApp AI Secretary", lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "running", "service": "WhatsApp AI Secretary"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        body = await request.json()
        logger.info(f"Webhook received: {body.get('typeWebhook', 'unknown')}")
        if body.get("typeWebhook") == "incomingMessageReceived":
            await handle_incoming_message(body)
        return JSONResponse({"status": "ok"})
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
