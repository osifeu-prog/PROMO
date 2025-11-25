import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, Depends
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from telegram import Update
from telegram.ext import Application

from app.database import Base, engine, get_db
from app.bot import setup_handlers
from app import crud, schemas

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Ensure DB schema exists
Base.metadata.create_all(bind=engine)

TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]  # e.g. https://web-production-xxxx.up.railway.app

ptb_app: Application = Application.builder().token(TOKEN).build()
setup_handlers(ptb_app)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Telegram application and setting webhook...")
    await ptb_app.initialize()
    await ptb_app.start()
    await ptb_app.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")
    logger.info("Webhook set to %s/%s", WEBHOOK_URL, TOKEN)
    yield
    # Shutdown
    logger.info("Shutting down Telegram application...")
    await ptb_app.bot.delete_webhook()
    await ptb_app.stop()
    await ptb_app.shutdown()
    logger.info("Telegram application stopped.")


app = FastAPI(lifespan=lifespan)

# Serve the investor one-pager from /docs
app.mount("/docs", StaticFiles(directory="docs", html=True), name="docs")


@app.post(f"/{TOKEN}")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, ptb_app.bot)
    await ptb_app.process_update(update)
    return Response(status_code=200)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "PROMO investors bot"}


@app.get("/api/stats", response_model=schemas.StatsOut)
def api_stats(db: Session = Depends(get_db)):
    """Public stats endpoint – can be used by dashboards / landing page."""
    return crud.get_stats(db)
