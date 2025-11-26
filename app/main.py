import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, Depends
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from telegram import Update
from telegram.ext import Application

from app.database import Base, engine, get_db
from app import crud
from app.schemas import StatsOut
from app.bot import setup_handlers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Create DB tables on startup
Base.metadata.create_all(bind=engine)

TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "").rstrip("/")

if not WEBHOOK_URL:
    raise RuntimeError("WEBHOOK_URL environment variable is required")

# Telegram Application (python-telegram-bot 20.x)
ptb_app: Application = Application.builder().token(TOKEN).build()
setup_handlers(ptb_app)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start and stop the Telegram bot together with FastAPI."""
    logger.info("Starting Telegram Application...")
    await ptb_app.initialize()
    await ptb_app.start()
    webhook_url = f"{WEBHOOK_URL}/{TOKEN}"
    await ptb_app.bot.set_webhook(webhook_url)
    logger.info("Webhook set to %s", webhook_url)

    try:
        yield
    finally:
        logger.info("Shutting down Telegram Application...")
        try:
            await ptb_app.bot.delete_webhook()
        except Exception as e:
            logger.warning("Failed to delete webhook: %s", e)
        await ptb_app.stop()
        await ptb_app.shutdown()
        logger.info("Telegram Application stopped.")


app = FastAPI(
    lifespan=lifespan,
    title="SLH Ecosystem – Investor & Bot API",
    description=(
        "SLH investor bot, /investors landing page, and API statistics over Postgres.\n"
        "Built on FastAPI + python-telegram-bot + SQLAlchemy."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Static investor page
# /investors -> docs/index.html
app.mount(
    "/investors",
    StaticFiles(directory="docs", html=True),
    name="investors",
)

# Optionally serve hero image and others also under /assets
# (docs/style.css already points to docs/images/hero.jpg)
app.mount(
    "/assets",
    StaticFiles(directory="docs/images"),
    name="assets",
)


@app.post(f"/{TOKEN}")
async def telegram_webhook(request: Request):
    """Webhook endpoint for Telegram bot (POST only)."""
    data = await request.json()
    update = Update.de_json(data, ptb_app.bot)
    await ptb_app.process_update(update)
    return Response(status_code=200)


@app.get("/health")
async def health():
    """Simple health check for Railway."""
    return {
        "status": "ok",
        "service": "SLH PROMO investors bot",
        "webhook": f"{WEBHOOK_URL}/{TOKEN}",
    }


@app.get("/api/stats", response_model=StatsOut)
def api_stats(db: Session = Depends(get_db)):
    """Aggregated statistics for admin / investors dashboards."""
    return crud.get_stats(db)
