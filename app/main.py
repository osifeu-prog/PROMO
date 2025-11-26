import os
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


# ========== CONFIG & DB ==========

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "").rstrip("/")  # למשל: https://web-production-112f6.up.railway.app


def reset_db() -> None:
    """
    איפוס מלא של הסכמה מהקוד (רק כשאין לך עדיין נתונים חשובים!).
    מוחק את כל הטבלאות ובונה אותן מחדש לפי המודלים הנוכחיים.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


# ⚠️ כרגע – מפעילים reset_db בתחילת הריצה.
# אחרי שהפרויקט עולה לפרודקשן אמיתי ויש כבר נתונים, כדאי להסיר/להעיר שורה זו.
reset_db()


# ========== TELEGRAM APPLICATION ==========

ptb_app = Application.builder().token(BOT_TOKEN).build()
setup_handlers(ptb_app)  # טעינת כל ה-handlers של הבוט


# ========== FASTAPI LIFESPAN ==========

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    מנהל את מחזור החיים של האפליקציה:
    - אתחול ושיגור הבוט
    - סט והסרה של webhook
    """
    # אתחול הבוט
    await ptb_app.initialize()

    # סט webhook לטלגרם – מגדיר לאן טלגרם ישלח עדכונים
    if WEBHOOK_URL:
        await ptb_app.bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

    # התחלת הבוט (לוגיקה פנימית של PTB – לא polling, אלא רק הכנת האפליקציה)
    await ptb_app.start()

    try:
        yield
    finally:
        # ניקוי – הסרת webhook וסגירת האפליקציה
        try:
            await ptb_app.bot.delete_webhook()
        except Exception:
            pass

        await ptb_app.stop()
        await ptb_app.shutdown()


# ========== FASTAPI APP ==========

app = FastAPI(
    title="SLH Investor Bot & Landing",
    version="0.1.0",
    lifespan=lifespan,
)

# דף משקיעים סטטי – docs/index.html
app.mount(
    "/investors",
    StaticFiles(directory="docs", html=True),
    name="investors",
)

# אם תרצה לגשת ישירות לתמונת ה-Hero או לנכסים אחרים:
app.mount(
    "/assets",
    StaticFiles(directory="docs/images"),
    name="assets",
)


# ========== ROUTES ==========

@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    """
    נקודת Webhook שאליה טלגרם שולח עדכונים.
    Railway צריך לדעת להפנות את ה-POST הזה לפה.
    """
    data = await request.json()
    update = Update.de_json(data, ptb_app.bot)
    await ptb_app.process_update(update)
    return Response(status_code=200)


@app.get("/health")
async def health_check():
    """
    בדיקת חיים ל-Railway.
    """
    return {"status": "ok"}


@app.get("/api/stats", response_model=StatsOut)
def api_stats(db: Session = Depends(get_db)):
    """
    API קטן לסטטיסטיקות – אפשר להציג בעתיד בדשבורד משקיעים.
    """
    stats = crud.get_stats(db)
    return StatsOut(**stats)
