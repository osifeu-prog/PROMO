import logging
import random
import os
from pathlib import Path
from enum import Enum
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.orm import Session
from app.database import get_db
from app.crud import get_user_by_telegram_id, create_user, make_admin, create_portfolio, create_transaction
from app.utils import verify_password
from app.models import Link
from app.schemas import UserCreate, PortfolioCreate

# לוגים
logger = logging.getLogger(__name__)

# קונפיגורציה דרך משתני סביבה
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", 0))
PAYMENT_GROUP_ID = int(os.environ.get("PAYMENT_GROUP_ID", 0))
COMMUNITY_GROUP_ID = int(os.environ.get("COMMUNITY_GROUP_ID", 0))
SITE_URL = os.environ.get("SITE_URL", "https://yourusername.github.io/repo/")

# קישורים מוגדרים מראש
LINKS = [
    {"title": "Slh_selha_bot", "url": "https://t.me/Slh_selha_bot"},
    {"title": "BUY_MY_SHOP", "url": "https://t.me/BUY_MY_SHOP"},
    {"title": "NFTY_madness_bot", "url": "https://t.me/NFTY_madness_bot"},
    {"title": "קבוצת קהילת הבורסה", "url": "https://t.me/+HIzvM8sEgh1kNWY0"},
    {"title": "crypto_A_bot", "url": "https://t.me/crypto_A_bot"},
    {"title": "אתר ראשי: SLH", "url": SITE_URL},
    {"title": "SLH_Academia_bot", "url": "https://t.me/SLH_Academia_bot"},
    {"title": "YouTube Channel", "url": "https://www.youtube.com/channel/UC..."},  # עדכן URL מלא
]

# תמונות רנדומליות מהאינטרנט
EYE_CATCHING_IMAGES = [
    "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1621417201921-5d9a8f8f9e3d?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1605902711622-cfb43c4437b5?auto=format&fit=crop&w=1200&q=80",
]

# טקסט אודות נטען מקובץ חיצוני (docs/about.md)
ABOUT_TEXT = Path("docs/about.md").read_text(encoding="utf-8")

# Enum ל-callbacks
class Callback(str, Enum):
    ABOUT = "about"
    CONTENT = "content"
    COINS = "coins"
    GAMES = "games"
    EXPERTS = "experts"
    INVEST = "invest"
    ADMIN = "admin"
    REQUEST_ADMIN = "request_admin"
    INVEST_NOW = "invest_now"
    INVEST_PANEL = "invest_panel"

def setup_handlers(ptb):
    ptb.add_handler(CommandHandler("start", start))
    ptb.add_handler(CommandHandler("login", admin_login))
    ptb.add_handler(CommandHandler("request_admin", request_admin))
    ptb.add_handler(CallbackQueryHandler(callback_handler))
    ptb.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

def build_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 אודות הפרויקט", callback_data=Callback.ABOUT)],
        [InlineKeyboardButton("📚 תוכן ואקדמיה", callback_data=Callback.CONTENT)],
        [InlineKeyboardButton("💰 מטבעות ומסחר", callback_data=Callback.COINS)],
        [InlineKeyboardButton("🎮 משחקים ו-NFT", callback_data=Callback.GAMES)],
        [InlineKeyboardButton("🧑‍💼 מערכת מומחים", callback_data=Callback.EXPERTS)],
        [InlineKeyboardButton("📈 השקעות כבדות", callback_data=Callback.INVEST)],
        [InlineKeyboardButton("🔗 בקר באתר", url=SITE_URL)],
        [InlineKeyboardButton("🔒 אדמין (מורשים)", callback_data=Callback.ADMIN)],
        [InlineKeyboardButton("🛡️ בקש גישה אדמין", callback_data=Callback.REQUEST_ADMIN)],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = next(get_db())):
    user_id = update.effective_user.id
    user = get_user_by_telegram_id(db, user_id)
    if not user:
        user = create_user(db, UserCreate(telegram_id=user_id, username=update.effective_user.username))
    if user_id == ADMIN_USER_ID and not user.is_admin:
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
    user = get_user_by_telegram_id(db, query.from_user.id)

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
        invest_keyboard = [
            [InlineKeyboardButton(link['title'], url=link['url']) for link in LINKS[:3]],
            [InlineKeyboardButton("השקע עכשיו (מ-10,000 ש\"ח)", callback_data=Callback.INVEST_NOW)],
            [InlineKeyboardButton("פאנל השקעות VIP", callback_data=Callback.INVEST_PANEL)],
        ]
        await query.edit_message_text("📈 השקעות כבדות: גיוס 10 מיליון ש\"ח עם דיבידנטים ושותפות מלאה.", reply_markup=InlineKeyboardMarkup(invest_keyboard))
    elif data == Callback.INVEST_NOW:
        await query.message.reply_text("צור קשר להשקעה: שלח סכום (מ-10,000 ש\"ח) ופרטים. אישור חוזה חכם בקבוצת תשלומים.")
    elif data == Callback.INVEST_PANEL:
        transactions = user.transactions if user else []
        text = "פאנל השקעות VIP:\n" + "\n".join([f"עסקה {t.id}: {t.amount} ש\"ח, סטטוס: {t.status}" for t in transactions])
        await query.edit_message_text(text or "אין עסקאות כרגע.")
    elif data == Callback.ADMIN:
        if user and user.is_admin:
            admin_keyboard = [
                [InlineKeyboardButton("עדכן תוכן", callback_data="admin_update")],
                [InlineKeyboardButton("הוסף קישור", callback_data="admin_add_link")],
                [InlineKeyboardButton("נהל משתמשים", callback_data="admin_users")],
                [InlineKeyboardButton("אשר השקעות", callback_data="admin_approve")],
                [InlineKeyboardButton("שנה סיסמה", callback_data="admin_pass")],
            ]
            await query.edit_message_text("פאנל אדמין מתקדם – נהל את האקוסיסטם!", reply_markup=InlineKeyboardMarkup(admin_keyboard))
        else:
            await query.answer("גישה מוגבלת – בקש אישור.")
    elif data == Callback.REQUEST_ADMIN:
        await query.message.reply_text("בקשת אדמין נשלחה לקבוצה. נדון בחוזה חכם דרך הבוט.")

async def request_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(COMMUNITY_GROUP_ID, f"בקשת אדמין חדשה מ-{update.effective_user.username}! נהל דיון וחוזה חכם כאן.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = next(get_db())):
    chat_id = update.message.chat_id
    if chat_id == PAYMENT_GROUP_ID:
        await context.bot.send_message(ADMIN
