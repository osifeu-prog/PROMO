import os
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import Application

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.bot import setup_handlers
from app.database import engine, Base, get_db


# ----------------------------------------------------------------------
# Logging configuration
# ----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("app.main")


# ----------------------------------------------------------------------
# Environment / settings
# ----------------------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "").rstrip("/")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "production").lower()

if not BOT_TOKEN:
    # בלי טוקן אין בוט – נכשלים מיד
    raise RuntimeError("BOT_TOKEN environment variable is required")


# ----------------------------------------------------------------------
# Database – יצירת הטבלאות (אם לא קיימות)
# ----------------------------------------------------------------------
Base.metadata.create_all(bind=engine)


# ----------------------------------------------------------------------
# Telegram Application setup
# ----------------------------------------------------------------------
ptb_app: Application = Application.builder().token(BOT_TOKEN).build()
setup_handlers(ptb_app)


# ----------------------------------------------------------------------
# FastAPI app with lifespan – ניהול Webhook ו-PTB
# ----------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup / Shutdown:
    - אתחול אפליקציית טלגרם
    - וידוא שה-webhook מצביע על הכתובת של Railway
    - כיבוי מסודר
    """
    logger.info("Starting application (environment=%s)", ENVIRONMENT)

    # Initialize PTB application
    await ptb_app.initialize()

    # Set webhook only if WEBHOOK_URL provided
    if WEBHOOK_URL:
        webhook_target = f"{WEBHOOK_URL}/{BOT_TOKEN}"
        try:
            info = await ptb_app.bot.get_webhook_info()
            if info.url != webhook_target:
                await ptb_app.bot.set_webhook(
                    url=webhook_target,
                    allowed_updates=["message", "callback_query"],
                )
                logger.info("Webhook set to %s", webhook_target)
            else:
                logger.info("Webhook already set correctly: %s", webhook_target)
        except Exception as e:
            logger.error("Failed to set webhook", exc_info=e)
            # לא מרימים כאן exception כדי שלא יפיל את השרת
    else:
        logger.warning("WEBHOOK_URL not defined – bot will not receive updates")

    # Start PTB internal components (no polling – רק webhook)
    await ptb_app.start()
    logger.info("Telegram Application started")

    try:
        yield
    finally:
        logger.info("Shutting down application...")
        try:
            if WEBHOOK_URL:
                await ptb_app.bot.delete_webhook(drop_pending_updates=True)
                logger.info("Webhook deleted")
        except Exception as e:
            logger.warning("Failed to delete webhook on shutdown", exc_info=e)

        await ptb_app.stop()
        await ptb_app.shutdown()
        logger.info("Application shutdown complete")


app = FastAPI(
    lifespan=lifespan,
    title="SLH / SELA Investor Bot",
    version="0.1.0",
)


# ----------------------------------------------------------------------
# Middleware
# ----------------------------------------------------------------------
# CORS – כרגע פתוח, אפשר לצמצם אח"כ
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted hosts – מברירת מחדל מאפשר הכל, אפשר להגדיר ב-ENV
trusted_hosts_env = os.environ.get("TRUSTED_HOSTS", "*")
trusted_hosts = [h.strip() for h in trusted_hosts_env.split(",")] if trusted_hosts_env else ["*"]

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=trusted_hosts,
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error("Unhandled application error", exc_info=e)
        raise
    process_time = time.time() - start_time
    logger.info(
        "%s %s - %s (%.3fs)",
        request.method,
        request.url.path,
        getattr(response, "status_code", "unknown"),
        process_time,
    )
    return response


# ----------------------------------------------------------------------
# Static investor page – /investors (docs/)
# ----------------------------------------------------------------------
# בריילווי המבנה הוא: /app/app/main.py ו- /app/docs
if os.path.isdir("docs"):
    app.mount("/investors", StaticFiles(directory="docs", html=True), name="investors")
    logger.info("Mounted /investors static route from ./docs")
else:
    logger.warning("docs directory not found – /investors will not serve a page")


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def root():
    """
    אם יש docs – נשלח ל-/investors.
    אחרת מחזירים JSON בסיסי.
    """
    if os.path.isdir("docs"):
        return RedirectResponse(url="/investors")
    return {"status": "ok", "service": "SLH / SELA Investor Bot"}


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check עבור Railway.
    תמיד מחזיר 200, אבל מציין סטטוס DB ובוט.
    """
    health: Dict[str, Any] = {
        "status": "ok",
        "environment": ENVIRONMENT,
    }

    # DB check
    try:
        db.execute(text("SELECT 1"))
        health["database"] = "connected"
    except Exception as e:
        logger.error("Database health check failed", exc_info=e)
        health["database"] = "error"
        health["status"] = "degraded"

    # Telegram bot basic check (non-fatal)
    try:
        me = await ptb_app.bot.get_me()
        health["telegram_bot"] = "connected"
        health["bot_username"] = me.username
    except Exception as e:
        logger.error("Telegram bot health check failed", exc_info=e)
        health["telegram_bot"] = "error"
        health["status"] = "degraded"

    return JSONResponse(content=health)


@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    """
    נקודת ה-webhook של טלגרם.
    """
    try:
        raw_body = await request.body()
        logger.debug("Webhook received (%d bytes)", len(raw_body))

        if len(raw_body) > 1024 * 1024:  # 1MB
            logger.warning("Webhook payload too large")
            raise HTTPException(status_code=413, detail="Payload too large")

        try:
            data = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in webhook", exc_info=e)
            raise HTTPException(status_code=400, detail="Invalid JSON")

        update = Update.de_json(data, ptb_app.bot)
        await ptb_app.process_update(update)

        # טלגרם לא צריך תוכן – רק 200
        return Response(status_code=200)

    except HTTPException:
        # כבר עטפנו – מעבירים הלאה
        raise
    except TelegramError as e:
        logger.error("Telegram API error while processing webhook", exc_info=e)
        raise HTTPException(status_code=502, detail="Telegram API error")
    except Exception as e:
        logger.error("Unexpected error in webhook handler", exc_info=e)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/stats")
async def api_stats():
    """
    placeholder – כדי ש- /api/stats לא יחזיר 404.
    אפשר לחבר ל-crud.get_stats בהמשך.
    """
    return {"message": "stats endpoint not yet implemented"}
