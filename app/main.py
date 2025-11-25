from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException
from telegram import Update
from telegram.ext import Application
from sqlalchemy.orm import Session
from app.bot import setup_handlers  # Import to add handlers
from app.database import engine, Base, get_db
import os
import asyncio

# Create DB tables
Base.metadata.create_all(bind=engine)

TOKEN = os.environ['BOT_TOKEN']
WEBHOOK_URL = os.environ['WEBHOOK_URL']  # e.g., https://your-domain.railway.app

ptb = Application.builder().token(TOKEN).read_timeout(7).get_updates_read_timeout(42).build()

setup_handlers(ptb)  # Add all handlers

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await ptb.initialize()
    await ptb.start()
    await ptb.updater.start_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        url_path=TOKEN,
        webhook_url=WEBHOOK_URL + "/" + TOKEN  # Add slash if needed
    )
    yield
    # Shutdown
    await ptb.updater.stop()
    await ptb.stop()
    await ptb.shutdown()

app = FastAPI(lifespan=lifespan)

@app.post(f"/{TOKEN}")
async def webhook(request: Request):
    json = await request.json()
    update = Update.de_json(json, ptb.bot)
    await ptb.process_update(update)
    return Response(status_code=200)

# Optional: Health check endpoint
@app.get("/")
async def health():
    return {"status": "ok"}
