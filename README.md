import os
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, Depends
from fastapi.staticfiles import StaticFiles
from telegram import Update
from telegram.ext import Application
from sqlalchemy.orm import Session

from app.database import engine, Base, get_db
from app.bot import setup_handlers
from app import crud
from app.schemas import StatsOut

logger = logging.getLogger("app.main")
logging.basicConfig(level=logging.INFO)

# ========= CONFIG =========

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "").rstrip("/")  # למשל: https://web-production-112f6.up.railway.app


# ========= DB INIT =========
# כאן אנחנו דואגים שהסכמה תהיה לפי ה-Models (כולל BigInteger),
# אבל בצורה שלא מפילה את השרת אם יש בעיה בחיבור ל-DB.

def init_db() -> None:
    try:
        logger.info("Dropping all tables (if exist)...")
        Base.metadata.drop_all(bind=engine)
    except Exception as e:
        logger.warning("drop_all failed (ignored): %s", e)

    try:
        logger.info("Creating all tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("DB schema initialized.")
    except Exception as e:
        logger.error("create_all failed: %s", e)


# מריצים פעם אחת בזמן עליית האפליקציה (בייבוא המודול)
init_db()


# ========= TELEGRAM APPLICATION =========

ptb_app = Application.builder().token(BOT_TOKEN).build()
setup_handlers(ptb_app)


# ========= LIFESPAN =========

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Telegram Application...")
    await ptb_app.initialize()

    if WEBHOOK_URL:
        hook_url = f"{WEBHOOK_URL}/{BOT_TOKEN}"
        await ptb_app.bot.set_webhook(url=hook_url)
        logger.info("Webhook set to %s", hook_url)

    await ptb_app.start()

    try:
        yield
    finally:
        try:
            await ptb_app.bot.delete_webhook()
        except Exception as e:
            logger.warning("Failed to delete webhook: %s", e)

        await ptb_app.stop()
        await ptb_app.shutdown()
        logger.info("Telegram Application stopped.")


# ========= FASTAPI APP =========

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

# נכסים סטטיים (רק אם התיקייה באמת קיימת – כדי לא להפיל את השרת)
if os.path.isdir("docs/images"):
    app.mount(
        "/assets",
        StaticFiles(directory="docs/images"),
        name="assets",
    )
else:
    logger.warning("docs/images not found, skipping /assets mount")


# ========= ROUTES =========

@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    """
    נקודת Webhook שמטפלת בכל העדכונים מטלגרם.
    נוספו לוגים כדי לראות בריילווי אם בכלל מגיעות בקשות.
    """
    raw_body = await request.body()
    logger.info("Webhook hit, raw body size=%d bytes", len(raw_body))

    try:
        data = json.loads(raw_body.decode("utf-8"))
    except Exception:
        logger.exception("Failed to parse webhook JSON")
        return Response(status_code=400)

    try:
        update = Update.de_json(data, ptb_app.bot)
        await ptb_app.process_update(update)
    except Exception:
        logger.exception("Error while processing Telegram update")
        return Response(status_code=500)

    return Response(status_code=200)


@app.get("/")
async def root():
    # להפנות את מי שנכנס ישירות לדומיין לדף המשקיעים
    return Response(
        status_code=307,
        headers={"Location": "/investors"},
    )


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/stats", response_model=StatsOut)
def api_stats(db: Session = Depends(get_db)):
    stats = crud.get_stats(db)
    return StatsOut(**stats)



















    
