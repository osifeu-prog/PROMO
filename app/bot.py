import logging
import random
from pathlib import Path
from enum import Enum
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.orm import Session
from app.database import get_db
from app.crud import get_user_by_telegram_id, create_user, make_admin
from app.schemas import UserCreate
from app.config import settings  # ניהול משתני סביבה

logger = logging.getLogger(__name__)

# תמונות רלוונטיות מהאינטרנט
EYE_CATCHING_IMAGES = [
    "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1621417201921-5d9a8f8f9e3d?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1605902711622-cfb43c4437b5?auto=format&fit=crop&w=1200&q=80",
]

ABOUT_TEXT = Path("docs/about.md").read_text(encoding="utf-8")

class Callback(str, Enum):
    ABOUT = "about"
    CONTENT = "content"
    COINS = "coins"
    GAMES = "games"
    EXPERTS = "experts"
    INVEST = "invest"
    ADMIN = "admin"
    REQUEST_ADMIN = "request_admin"

def build_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 אודות הפרויקט", callback_data=Callback.ABOUT)],
        [InlineKeyboardButton("📚 תוכן ואקדמיה", callback_data=Callback.CONTENT)],
        [InlineKeyboardButton("💰 מטבעות ומסחר", callback_data=Callback.COINS)],
        [InlineKeyboardButton("🎮 משחקים ו-NFT", callback_data=Callback.GAMES)],
        [InlineKeyboardButton("🧑‍💼 מערכת מומחים", callback_data=Callback.EXPERTS)],
        [InlineKeyboardButton("📈 השקעות כבדות", callback_data=Callback.INVEST)],
        [InlineKeyboardButton("🔗 בקר באתר", url=settings.site_url)],
        [InlineKeyboardButton("🔒 אדמין (מורשים)", callback_data=Callback.ADMIN)],
        [InlineKeyboardButton("🛡️ בקש גישה אדמין", callback_data=Callback.REQUEST_ADMIN)],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = next(get_db())):
    user_id = update.effective_user.id
    user = get_user_by_telegram_id(db, user_id)
    if not user:
        user = create_user(db, UserCreate(telegram_id=user_id, username=update.effective_user.username))
    if user_id == settings.admin_user_id and not user.is_admin:
        make_admin(db, user_id, "admin123")

    image_url = random.choice(EYE_CATCHING_IMAGES)
    try:
        await update.message.reply_photo(photo=image_url, caption="🚀 הצטרפו למהפכה הדיגיטלית של SLH 🚀")
    except Exception as e:
        logger.error(f"Failed to send photo: {e}")
        await update.message.reply_text("🚀 הצטרפו למהפכה הדיגיטלית של SLH 🚀")

    await update.message.reply_text("גלה את העתיד הכלכלי: SLH – אקוסיסטם AI מבוסס אמון!", reply_markup=build_main_menu())

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = next(get_db())):
    query = update.callback_query
    data = query.data

    if data == Callback.ABOUT:
        await query.edit_message_text(ABOUT_TEXT)
    elif data == Callback.CONTENT:
        await query.edit_message_text("📚 תוכן ואקדמיה SLH: קורסים מקוונים בכלכלה בריאה, AI ופסיכולוגיה.")
    elif data == Callback.COINS:
        await query.edit_message_text("💰 מטבעות SLH: מטבע פנימי עם סטייקינג וחיבור ל-BSC ו-TON.")
    elif data == Callback.GAMES:
        await query.edit_message_text("🎮 משחקים: תשתית ארקייד, קזינו נקודות ו-NFT.")
    elif data == Callback.EXPERTS:
        await query.edit_message_text("🧑‍💼 מערכת מומחים: AI לבחירת שותפים ומנטורים.")
    elif data == Callback.INVEST:
        await query.edit_message_text("📈 השקעות כבדות: גיוס 10 מיליון ש\"ח עם דיבידנטים ושותפות מלאה.")
    elif data == Callback.ADMIN:
        await query.answer("גישה מוגבלת – בקש אישור.")
    elif data == Callback.REQUEST_ADMIN:
        await query.message.reply_text("בקשת אדמין נשלחה לקבוצה.")
