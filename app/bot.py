import logging
import os
from enum import Enum

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    Application,
    ContextTypes,
    MessageHandler,
    filters,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, schemas
from app.models import User

logger = logging.getLogger(__name__)

ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", "0"))
PAYMENT_GROUP_ID = int(os.environ.get("PAYMENT_GROUP_ID", "0"))
COMMUNITY_GROUP_ID = int(os.environ.get("COMMUNITY_GROUP_ID", "0"))

DOCS_URL = os.environ.get("DOCS_URL", "https://web-production-112f6.up.railway.app/docs")

class Callback(str, Enum):
    ABOUT = "about"
    MODEL = "model"
    PORTFOLIO = "portfolio"
    CONTACT = "contact"
    ADMIN_PANEL = "admin_panel"
    ADMIN_STATS = "admin_stats"

# --- Helpers ---

def _get_or_create_user(db: Session, update: Update) -> User:
    tg_user = update.effective_user
    if not tg_user:
        raise RuntimeError("No Telegram user in update")
    user = crud.get_user_by_telegram_id(db, tg_user.id)
    if not user:
        user = crud.create_user(
            db,
            schemas.UserCreate(telegram_id=tg_user.id, username=tg_user.username or ""),
            is_admin=(tg_user.id == ADMIN_USER_ID),
        )
    return user

async def _reply_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("מה זו האימפריה של SLH?", callback_data=Callback.ABOUT),
        ],
        [
            InlineKeyboardButton("מודל ההשקעה והגיוס", callback_data=Callback.MODEL),
        ],
        [
            InlineKeyboardButton("שליחת פרטי משקיע/פורטפוליו", callback_data=Callback.PORTFOLIO),
        ],
        [
            InlineKeyboardButton("דברו איתנו ישירות", callback_data=Callback.CONTACT),
        ],
    ]
    if update.effective_user and update.effective_user.id == ADMIN_USER_ID:
        keyboard.append(
            [InlineKeyboardButton("🔐 פאנל אדמין", callback_data=Callback.ADMIN_PANEL)]
        )

    text = (
        "ברוך הבא לבוט המשקיעים של <b>SLH / SELA</b> 👋\n\n"
        "כאן מרוכז כל <b>התוכן</b>, המידע והחיבורים למשקיעים גדולים שרוצים להיכנס "
        "ללב האקו-סיסטם הכלכלי שלנו.\n\n"
        "בחר אחת מהאפשרויות בתפריט:"
    )
    await update.effective_chat.send_message(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db: Session = next(get_db())
    try:
        _get_or_create_user(db, update)
    finally:
        db.close()
    await _reply_main_menu(update, context)

async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db: Session = next(get_db())
    try:
        user = _get_or_create_user(db, update)
        await update.effective_chat.send_message(
            f"ID: {user.telegram_id}\n"
            f"Username: @{user.username}\n"
            f"Admin: {'כן' if user.is_admin else 'לא'}"
        )
    finally:
        db.close()

class CallbackData(str, Enum):
    pass  # kept for backward compatibility if needed

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    chat = query.message.chat

    if data == Callback.ABOUT:
        text = (
            "🔵 <b>SLH / SELA – Human Capital Protocol</b>\n\n"
            "אנחנו בונים אימפריה כלכלית שמחברת בין:\n"
            "• קהילות עסקיות ויזמים\n"
            "• פלטפורמת תוכן והכשרות חכמה\n"
            "• אקו-סיסטם של בוטים, ארנקים, NFT ו-DeFi\n\n"
            "הבוט הזה הוא שער לכניסה כמשקיע גדול – עם מבט גבוה על כל המערכת.\n\n"
            f"לקבלת תמונת מאקרו מלאה, אפשר לקרוא את מסמך המשקיעים שלנו כאן:\n{DOCS_URL}"
        )
        await chat.edit_message_text(text, parse_mode="HTML", reply_markup=query.message.reply_markup)
    elif data == Callback.MODEL:
        text = (
            "📈 <b>מודל ההשקעה</b>\n\n"
            "• גיוס מטרה: <b>10M ₪</b> בסבב משקיעים סגור.\n"
            "• שימוש בכסף: הרחבת התשתיות, פיתוח בוטים, תוכן, אקדמיה ופלטפורמת SLH Exchange.\n"
            "• שקיפות מלאה בגיבוי DB ו-Contracts חכמים (Hash) לכל משקיע.\n\n"
            "ניתן להציג בזמן אמת סטטיסטיקות וצמיחה (דרך פאנל האדמין וה-API הפנימי)."
        )
        await chat.edit_message_text(text, parse_mode="HTML", reply_markup=query.message.reply_markup)
    elif data == Callback.PORTFOLIO:
        text = (
            "🧩 <b>שליחת פרטי משקיע</b>\n\n"
            "שלח כאן הודעה חופשית עם:\n"
            "• סכום השקעה משוער\n"
            "• טווח זמן\n"
            "• ניסיון/תחומי עניין\n\n"
            "אנחנו ניצור עבורך כרטיס משקיע במערכת ונחזור אליך מתוך הקבוצה הסגורה."
        )
        await chat.edit_message_text(text, parse_mode="HTML", reply_markup=query.message.reply_markup)
    elif data == Callback.CONTACT:
        text = (
            "📞 <b>יצירת קשר ישיר</b>\n\n"
            "צוות SLH זמין עבורך דרך קבוצת המשקיעים והקהילה.\n"
            "הבוט יקשר אותך לקבוצות ולדיון פרטני לאחר שנקבל את פרטי ההשקעה שלך.\n\n"
            "הקבוצות עצמן מנוהלות על גבי תשתית השרתים שלנו (Railway + Postgres) כדי להבטיח סדר ושקיפות."
        )
        await chat.edit_message_text(text, parse_mode="HTML", reply_markup=query.message.reply_markup)
    elif data == Callback.ADMIN_PANEL:
        if query.from_user.id != ADMIN_USER_ID:
            await query.answer("אין לך הרשאות לאדמין.", show_alert=True)
            return

        db: Session = next(get_db())
        try:
            stats = crud.get_stats(db)
        finally:
            db.close()

        text = (
            "🔐 <b>פאנל אדמין – SLH Investors</b>\n\n"
            f"סה"כ משקיעים במערכת: <b>{stats.total_users}</b>\n"
            f"מספר עסקאות מתועדות: <b>{stats.total_transactions}</b>\n"
            f"סכום מצטבר (לפי DB): <b>{stats.total_amount_usd:.2f} USD</b>\n\n"
            "ניתן להרחיב את הפאנל הזה לעוד מדדים ודוחות, או לחבר אותו ישירות ללוח מחוונים חיצוני."
        )
        keyboard = [
            [InlineKeyboardButton("רענון נתונים", callback_data=Callback.ADMIN_STATS)]
        ]
        await chat.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    elif data == Callback.ADMIN_STATS:
        if query.from_user.id != ADMIN_USER_ID:
            await query.answer("אין לך הרשאות לאדמין.", show_alert=True)
            return

        db: Session = next(get_db())
        try:
            stats = crud.get_stats(db)
        finally:
            db.close()

        text = (
            "📊 <b>נתוני מערכת מעודכנים</b>\n\n"
            f"משתמשים: {stats.total_users}\n"
            f"עסקאות: {stats.total_transactions}\n"
            f"סכום מצטבר: {stats.total_amount_usd:.2f} USD"
        )
        await query.edit_message_text(text, parse_mode="HTML")

async def portfolio_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """כל הודעה פרטית שלא פקודה – נשמרת כפורטפוליו/התעניינות."""
    if update.effective_chat.type not in ("private",):
        return

    db: Session = next(get_db())
    try:
        user = _get_or_create_user(db, update)
        body = update.message.text or ""
        portfolio = schemas.PortfolioCreate(
            title="Investor Inquiry",
            description=body,
            links=None,
        )
        crud.create_portfolio(db, user_id=user.id, portfolio=portfolio)
    finally:
        db.close()

    await update.message.reply_text(
        "קיבלנו את הפרטים שלך.\n"
        "אחד מחברי הצוות יחזור אליך מתוך קבוצת המשקיעים / בשיחה פרטית."
    )

async def payment_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """מאזין לקבוצת התשלום/אימות (לפי PAYMENT_GROUP_ID) ומתייג אדמין."""
    if update.effective_chat.id != PAYMENT_GROUP_ID:
        return

    msg = update.effective_message
    admin_mention = f"<a href='tg://user?id={ADMIN_USER_ID}'>אדמין</a>" if ADMIN_USER_ID else "אדמין"
    await context.bot.send_message(
        chat_id=COMMUNITY_GROUP_ID if COMMUNITY_GROUP_ID else update.effective_chat.id,
        text=(
            "📥 התקבלה הודעת תשלום/אישור בקבוצת התשלומים.\n\n"
            f"{admin_mention} – אנא בדוק את ההודעה הבאה:\n"
            f"{msg.text_html if msg.text else ''}"
        ),
        parse_mode="HTML",
    )

def setup_handlers(app: Application):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("whoami", whoami))

    app.add_handler(CallbackQueryHandler(button))

    # הודעות פרטיות – פורטפוליו / התעניינות
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, portfolio_message))

    # הודעות בקבוצת תשלומים
    app.add_handler(MessageHandler(filters.ChatType.GROUPS, payment_group_handler))

    return app
