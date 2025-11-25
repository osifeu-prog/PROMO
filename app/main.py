from contextlib import asynccontextmanager
from http import HTTPStatus
from fastapi import FastAPI, Request, Response, Depends
from telegram import Update
from telegram.ext import Application
from sqlalchemy.orm import Session
from app.bot import setup_handlers  # Import to add handlers
from app.database import engine, Base, get_db
import os

# Create DB tables
Base.metadata.create_all(bind=engine)

TOKEN = os.environ['BOT_TOKEN']
WEBHOOK_URL = os.environ['WEBHOOK_URL'] 

ptb = Application.builder().token(TOKEN).read_timeout(7).get_updates_read_timeout(42).build()

setup_handlers(ptb)  # Add all handlers

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with ptb:
        await ptb.start()
        await ptb.updater.start_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8000)),
            url_path=TOKEN,
            webhook_url=WEBHOOK_URL + TOKEN
        )
        yield
        await ptb.updater.stop()
        await ptb.stop()

app = FastAPI(lifespan=lifespan)

@app.post(f"/{TOKEN}")
async def webhook(request: Request):
    json = await request.json()
    update = Update.de_json(json, ptb.bot)
    await ptb.process_update(update)
    return Response(status_code=HTTPStatus.OK)
