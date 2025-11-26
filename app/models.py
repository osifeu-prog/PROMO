import os
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from telegram import Update
from telegram.ext import Application
from telegram.error import TelegramError

from app.database import engine, Base, get_db
from app.bot import setup_handlers
from app import crud
from app.schemas import StatsOut

# ---------- Logging basic setup ----------

logger = logging.getLogger("app.main")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# ---------- Simple settings layer (env-based) ----------


class Settings:
    """
    שכבת קונפיגורציה פשוטה שמרכזת את כל המשתנים החשובים.
    בנויה בסגנון של BaseSettings אבל בלי תלות בספריות חיצוניות.
    """

    def __init__(self) -> None:
        self.bot_token: str = os.environ.get("BOT_TOKEN", "")
        self.webhook_url: str = os.environ.get("WEBHOOK_URL", "").rstrip("/")
        self.environment: str = os.environ.get("ENVIRONMENT", "development")
        self.database_url: str = os.environ.get("DATABASE_URL", "")
        # האם לבצע reset DB אוטומטי ב-development
        self.reset_db_flag: bool = os.environ.get("RESET_DB", "false").lower() == "true"

        if not self.bot_token:
            raise RuntimeError("BOT_TOKEN is required in environment variables")

        if not self.database_url:
            # לא מפיל את האפליקציה, אבל נותן אזהרה ברורה
            logger.warning("DATABASE_URL is not set – check Railway Postgres configuration")


settings = Settings()

logger.info(
    "Loaded settings: ENV=%s, WEBHOOK_URL=%s, RESET_DB=%s",
    settings.environment,
    settings.webhook_url,
    settings.reset_db_flag,
)

BOT_TOKEN = settings.bot_token
WEBHOOK_URL = settings.webhook_url

# ---------- DB init (במקום reset_db גס) ----------


def init_db() -> None:
    """
    אתחול סכמת DB בצורה מבוקרת:
    - ב-development אפשר לבצע reset מלא אם RESET_DB=true
    - בשאר המצבים – רק create_all
    """
    try:
        if settings.environment == "development" and settings.reset_db_flag:
            logger.warning("Resetting database in development mode (drop_all + create_all)")
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
        else:
            logger.info("Ensuring database schema is created (create_all)")
            Base.metadata.create_all(bind=engine)

    except Exception as e:
        logger.error("Database initialization failed", exc_info=e)
        # לא נרים RuntimeError כדי ש-healthcheck יראה את המצב
        # אבל זה לוג רציני שמסמן שיש בעיה ב-DB.


init_db()

# ---------- Telegram Application ----------

ptb_app = Application.builder().token(BOT_TOKEN).build()
setup_handlers(ptb_app)


# ---------- Lifespan – ניהול webhook ומשאבים ----------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Telegram Application in %s mode", settings.environment)

    await ptb_app.initialize()

    # ניהול webhook חכם: מגדיר רק אם צריך
    if WEBHOOK_URL:
        hook_url = f"{WEBHOOK_URL}/{BOT_TOKEN}"
        try:
            webhook_info = await ptb_app.bot.get_webhook_info()
            if webhook_info.url != hook_url:
                await ptb_app.bot.set_webhook(url=hook_url)
                logger.info("Webhook set to %s", hook_url)
            else:
                logger.info("Webhook already set correctly: %s", hook_url)
        except Exception as e:
            logger.error("Failed to set webhook", exc_info=e)
            # כאן הגיוני להפיל את האפליקציה – בלי webhook אין בוט
            raise

    await ptb_app.start()
    logger.info("Application startup completed")

    try:
        yield
    finally:
        logger.info("Shutting down application...")
        try:
            if WEBHOOK_URL:
                await ptb_app.bot.delete_webhook(drop_pending_updates=True)
                logger.info("Webhook deleted")
        except Exception as e:
            logger.warning("Failed to delete webhook", exc_info=e)

        await ptb_app.stop()
        await ptb_app.shutdown()
        logger.info("Application shutdown completed")


# ---------- FastAPI App ----------

app = FastAPI(
    title="SLH Investor Bot & Landing",
    version="0.1.0",
    lifespan=lifespan,
)

# דף המשקיעים /investors (docs/index.html)
app.mount(
    "/investors",
    StaticFiles(directory="docs", html=True),
    name="investors",
)

# נכסים סטטיים – רק אם התיקייה קיימת (לא להפיל את השרת)
if os.path.isdir("docs/images"):
    app.mount(
        "/assets",
        StaticFiles(directory="docs/images"),
        name="assets",
    )
else:
    logger.warning("docs/images not found, skipping /assets mount")


# ---------- Middleware קטן ללוגי HTTP (ללא ספריות חיצוניות) ----------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        "%s %s -> %s (%.3fs)",
        request.method,
        request.url.path,
        response.status_code,
        process_time,
    )
    return response


# ---------- Routes ----------

@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    """
    נקודת Webhook שמטפלת בעדכוני טלגרם.
    כולל וולידציה בסיסית, לוגים, וטיפול בשגיאות.
    """
    try:
        raw_body = await request.body()
        logger.info("Webhook received (size=%d bytes)", len(raw_body))

        if len(raw_body) > 1024 * 1024:  # 1MB
            raise HTTPException(status_code=413, detail="Payload too large")

        data = json.loads(raw_body.decode("utf-8"))
        update = Update.de_json(data, ptb_app.bot)

        logger.debug("Processing update_id=%s", getattr(update, "update_id", None))

        await ptb_app.process_update(update)
        return Response(status_code=200)

    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in webhook", exc_info=e)
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except TelegramError as e:
        logger.error("Telegram API error", exc_info=e)
        raise HTTPException(status_code=502, detail="Telegram API error")
    except Exception as e:
        logger.error("Unexpected error in webhook", exc_info=e)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/")
async def root():
    """
    הפניה של הדומיין הראשי לדף המשקיעים.
    """
    return Response(status_code=307, headers={"Location": "/investors"})


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check ידידותי ל-Railway:
    - מצב כללי
    - בדיקת DB (SELECT 1)
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
    }

    try:
        db.execute("SELECT 1")
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = "disconnected"
        health_status["status"] = "unhealthy"
        logger.error("Database health check failed", exc_info=e)

    return health_status


@app.get("/api/stats", response_model=StatsOut)
def api_stats(db: Session = Depends(get_db)):
    """
    API לסטטיסטיקות – אפשר להרחיב בהמשך לפילטרים וכו'.
    """
    try:
        stats = crud.get_stats(db)
        return StatsOut(**stats)
    except Exception as e:
        logger.error("Failed to fetch statistics", exc_info=e)
        raise HTTPException(status_code=500, detail="Could not retrieve statistics")
