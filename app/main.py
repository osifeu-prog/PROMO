from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application
from sqlalchemy.orm import Session
from app.bot import setup_handlers  # Import to add handlers
from app.database import engine, Base, get_db
import os

# Create DB tables
Base.metadata.create_all(bind=engine)

TOKEN = os.environ['BOT_TOKEN']
WEBHOOK_URL = os.environ['WEBHOOK_URL']  # e.g., https://your-domain.railway.app

ptb = Application.builder().token(TOKEN).build()  # No read_timeout here, as we handle via FastAPI

setup_handlers(ptb)  # Add all handlers

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await ptb.initialize()
    if ptb.post_init:
        await ptb.post_init()
    yield
    # Shutdown
    if ptb.post_shutdown:
        await ptb.post_shutdown()
    await ptb.shutdown()

app = FastAPI(lifespan=lifespan)

@app.post(f"/{TOKEN}")
async def webhook(request: Request):
    json = await request.json()
    update = Update.de_json(json, ptb.bot)
    await ptb.process_update(update)
    return Response(status_code=200)

# Optional: Health check
@app.get("/health")
async def health_check():
    return {"status": "ok"}
