import logging
import os
from enum import Enum

from sqlalchemy.orm import Session
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from app.database import get_db
from app import crud
from app.schemas import UserCreate, PortfolioCreate

logger = logging.getLogger(__name__)

ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", "0"))
PAYMENT_GROUP_ID = int(os.environ.get("PAYMENT_GROUP_ID", "0"))
COMMUNITY_GROUP_ID = int(os.environ.get("COMMUNITY_GROUP_ID", "0"))

DOCS_URL = os.environ.get(
    "DOCS_URL",
    "https://web-production-112f6.up.railway.app/investors",
)
GITHUB_URL = os.environ.get(
    "GITHUB_URL",
    "https://github.com/osifeu-prog/PROMO",
)

# ניתן להחליף לקובץ סטטי בשרת שלך אם תרצה
HERO_IMAGE_URL = os.environ.get(
    "HERO_IMAGE_URL",
    "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?auto=format&fit=crop&w=1200&q=80",
)


class Callback(str, Enum):
    ABOUT = "about"
    MODEL = "model"
    PORTFOLIO = "portfolio"
    CONTACT = "contact"
    ADMIN_PANEL = "admin_panel"
    ADMIN_STATS = "admin_stats"


def _get_or_create_user(db: Session, update: Update):
    tg_user = update.effective_user
    if not tg_user:
        raise RuntimeError("No Telegram user in update")

    user = crud.get_user_by_telegram_id(db, tg_user.id)
    if not user:
        user = crud.create_user(
            db,
            UserCreate(
                telegram_id=tg_user.id,
                username=tg_user.username or "",
            ),
        )
    return user


async def _send_main_menu(chat, is_admin: bool = False):
    callback_rows = [
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

    url_row = [
        InlineKeyboardButton("🌐 דף המשקיעים", url=DOCS_URL),
        InlineKeyboardButton("💻 קוד המערכת (GitHub)", url=GITHUB_URL),
    ]

    if is_admin and ADMIN_USER_ID:
        callback_rows.append(
            [InlineKeyboardButton("🔐 פאנל אדמין", callback_data=Callback.ADMIN_PANEL)]
        )

    keyboard = callback_rows + [url_row]

    text = (
        "ברוך הבא לבוט המשקיעים של <b>SLH / SELA</b> 👋\n\n"
        "כאן מרוכז כל <b>התוכן</b>, המידע והחיבורים למשקיעים גדולים שרוצים להיכנס "
        "ללב האקו-סיסטם הכלכלי שלנו.\n\n"
        "בחר אחת מהאפשרויות בתפריט או פתח את דף המשקיעים לצפייה מלאה במודל."
    )

    await chat.send_photo(
        HERO_IMAGE_URL,
        caption=text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db: Session = next(get_db())
    try:
        user = _get_or_create_user(db, update)
        is_admin = user.telegram_id == ADMIN_USER_ID
    finally:
        db.close()

    chat = update.effective_chat
    await _send_main_menu(chat, is_admin=is_admin)


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db: Session = next(get_db())
    try:
        user = _get_or_create_user(db, update)
        is_admin = user.telegram_id == ADMIN_USER_ID
    finally:
        db.close()

    await update.effective_chat.send_message(
        f"ID: {user.telegram_id}\nUsername: @{user.username}\nAdmin: {'כן' if is_admin else 'לא'}"
    )


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
        await chat.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=query.message.reply_markup,
        )

    elif data == Callback.MODEL:
        text = (
            "📈 <b>מודל ההשקעה</b>\n\n"
            "• גיוס מטרה: <b>10M ₪</b> בסבב משקיעים סגור.\n"
            "• שימוש בכסף: הרחבת התשתיות, פיתוח בוטים, תוכן, אקדמיה ופלטפורמת SLH Exchange.\n"
            "• שקיפות מלאה בגיבוי DB ו-Contracts חכמים לכל משקיע.\n\n"
            "ניתן להציג בזמן אמת סטטיסטיקות וצמיחה (דרך פאנל האדמין וה-API הפנימי)."
        )
        await chat.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=query.message.reply_markup,
        )

    elif data == Callback.PORTFOLIO:
        text = (
            "🧩 <b>שליחת פרטי משקיע</b>\n\n"
            "שלח כאן הודעה חופשית עם:\n"
            "• סכום השקעה משוער\n"
            "• טווח זמן\n"
            "• ניסיון/תחומי עניין\n\n"
            "אנחנו ניצור עבורך כרטיס משקיע במערכת ונחזור אליך מתוך הקבוצה הסגורה."
        )
        await chat.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=query.message.reply_markup,
        )

    elif data == Callback.CONTACT:
        text = (
            "📞 <b>יצירת קשר ישיר</b>\n\n"
            "צוות SLH זמין עבורך דרך קבוצת המשקיעים והקהילה.\n"
            "הבוט יקשר אותך לקבוצות ולדיון פרטני לאחר שנקבל את פרטי ההשקעה שלך.\n\n"
            "הקבוצות עצמן מנוהלות על גבי תשתית השרתים שלנו (Railway + Postgres) כדי להבטיח סדר ושקיפות."
        )
        await chat.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=query.message.reply_markup,
        )

    elif data == Callback.ADMIN_PANEL:
        if not ADMIN_USER_ID or query.from_user.id != ADMIN_USER_ID:
            await query.answer("אין לך הרשאות לאדמין.", show_alert=True)
            return

        db: Session = next(get_db())
        try:
            stats = crud.get_stats(db)
        finally:
            db.close()

        text = (
            "🔐 <b>פאנל אדמין – SLH Investors</b>\n\n"
            f"סה\"כ משקיעים במערכת: <b>{stats['total_users']}</b>\n"
            f"מספר עסקאות מתועדות: <b>{stats['total_transactions']}</b>\n"
            f"סכום מצטבר (לפי DB): <b>{stats['total_amount_usd']:.2f} USD</b>\n\n"
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
        if not ADMIN_USER_ID or query.from_user.id != ADMIN_USER_ID:
            await query.answer("אין לך הרשאות לאדמין.", show_alert=True)
            return

        db: Session = next(get_db())
        try:
            stats = crud.get_stats(db)
        finally:
            db.close()

        text = (
            "📊 <b>נתוני מערכת מעודכנים</b>\n\n"
            f"משתמשים: {stats['total_users']}\n"
            f"עסקאות: {stats['total_transactions']}\n"
            f"סכום מצטבר: {stats['total_amount_usd']:.2f} USD"
        )
        await query.edit_message_text(text, parse_mode="HTML")


async def portfolio_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle free-text investor messages in private chat as portfolio entries."""
    if update.effective_chat.type != "private":
        return

    text = update.effective_message.text or ""
    if not text.strip():
        return

    db: Session = next(get_db())
    try:
        user = _get_or_create_user(db, update)
        portfolio = PortfolioCreate(
            title="Investor Inquiry",
            description=text,
            links=None,
        )
        crud.create_portfolio(db, user_id=user.id, portfolio=portfolio)
    finally:
        db.close()

    await update.effective_message.reply_text(
        "קיבלנו את הפרטים שלך. אחד מחברי הצוות יחזור אליך מתוך קבוצת המשקיעים / בשיחה פרטית."
    )


async def payment_group_bridge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bridge important messages from the payment group into the community / admin."""
    chat = update.effective_chat
    if chat.id != PAYMENT_GROUP_ID:
        return

    msg = update.effective_message
    text = msg.text_html or msg.caption_html or ""
    if not text:
        return

    target_chat_id = COMMUNITY_GROUP_ID or ADMIN_USER_ID
    if not target_chat_id:
        return

    admin_mention = (
        f"<a href='tg://user?id={ADMIN_USER_ID}'>אדמין</a>" if ADMIN_USER_ID else "אדמין"
    )

    await context.bot.send_message(
        chat_id=target_chat_id,
        text=(
            "📥 התקבלה הודעת תשלום/אישור בקבוצת התשלומים.\n\n"
            f"{admin_mention} – אנא בדוק את ההודעה הבאה:\n"
            f"{text}"
        ),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


def setup_handlers(app):
    """Attach all Telegram handlers to the Application instance."""
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("whoami", whoami))

    app.add_handler(CallbackQueryHandler(button))

    # Private messages from investors
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & (~filters.COMMAND),
            portfolio_message,
        )
    )

    # Group payment notifications bridge
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & (~filters.COMMAND),
            payment_group_bridge,
        )
    )

    return app
