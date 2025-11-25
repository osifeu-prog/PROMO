from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.orm import Session
from app.database import get_db
from app.crud import get_user_by_telegram_id, create_user, make_admin, create_portfolio, create_transaction
from app.utils import verify_password
from app.models import Link
from app.schemas import UserCreate, PortfolioCreate  # Import schemas here
import os

ADMIN_USER_ID = int(os.environ['ADMIN_USER_ID'])
PAYMENT_GROUP_ID = int(os.environ['PAYMENT_GROUP_ID'])
COMMUNITY_GROUP_ID = int(os.environ['COMMUNITY_GROUP_ID'])

# Predefined links (admins can add more via DB)
LINKS = [
    {"title": "Slh_selha_bot", "url": "https://t.me/Slh_selha_bot"},
    {"title": "BUY_MY_SHOP", "url": "https://t.me/BUY_MY_SHOP"},
    {"title": "NFTY_madness_bot", "url": "https://t.me/NFTY_madness_bot"},
    {"title": "קבוצת קהילת הבורסה", "url": "https://t.me/+HIzvM8sEgh1kNWY0"},
    {"title": "crypto_A_bot", "url": "https://t.me/crypto_A_bot"},
    {"title": "אתר ראשי: SLH", "url": "your_main_site_url"},  # Update
    {"title": "SLH_Academia_bot", "url": "https://t.me/SLH_Academia_bot"},
    {"title": "YouTube Channel", "url": "https://www.youtube.com/channel/..."},  # Add full URL
    # Add more from your list
]

ABOUT_TEXT = """
ברוכים הבאים ל-SLH - סלה ללא גבולות!
אקוסיסטם SLP שבו כל אדם יכול ליצור עסקים דיגיטליים.
נוצר ממטבע SLH, מבוסס אמון. 1000 SLH_TON = 1 SLH_BNB = 444 ש"ח.

אני, אוסיף אונגר: תארים בנירולוגיה, פסיכולוגיה, חינוך. מוסיקאי בינלאומי, האקר לבן, מתכנן AI, יוצר דיגיטלי.
תיק עבודות: [YouTube links], [Facebook links]  # Admins can update

שותף: [Add partner info]

פרויקטים נוספים: [List]
"""

def setup_handlers(ptb):
    ptb.add_handler(CommandHandler("start", start))
    ptb.add_handler(CommandHandler("login", admin_login))
    ptb.add_handler(CallbackQueryHandler(callback_handler))
    ptb.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    # Add more handlers for /invest, /lessons, etc.

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = next(get_db())):
    user_id = update.effective_user.id
    user = get_user_by_telegram_id(db, user_id)
    if not user:
        user = create_user(db, UserCreate(telegram_id=user_id, username=update.effective_user.username))
    if user_id == ADMIN_USER_ID and not user.is_admin:
        make_admin(db, user_id, "admin123")  # Change immediately

    # Send to community group (commented temporarily until group ID fixed)
    # await context.bot.send_message(COMMUNITY_GROUP_ID, f"משתמש חדש: @{user.username}")

    keyboard = [
        [InlineKeyboardButton("אודותינו", callback_data="about")],
        [InlineKeyboardButton("שיעורים", callback_data="lessons")],
        [InlineKeyboardButton("משקיעים", callback_data="invest")],
        [InlineKeyboardButton("אדמין (אם מורשה)", callback_data="admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("ברוכים הבאים לבוט שער SLH!", reply_markup=reply_markup)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = next(get_db())):
    query = update.callback_query
    data = query.data
    user = get_user_by_telegram_id(db, query.from_user.id)
    
    if data == "about":
        await query.answer()
        await query.edit_message_text(ABOUT_TEXT)
    elif data == "lessons":
        await query.answer()
        await query.edit_message_text("בקש גישה לשיעורים: /request_lesson [שם שיעור]")
    elif data == "invest":
        await query.answer()
        invest_keyboard = [
            [InlineKeyboardButton(link['title'], url=link['url']) for link in LINKS[:2]],  # Paginate if many
            # Add more rows
            [InlineKeyboardButton("השקע עכשיו", callback_data="invest_now")],
            [InlineKeyboardButton("פאנל ניהול", callback_data="invest_panel") if user else []],
        ]
        await query.edit_message_text("תפריט משקיעים: השקעה מ-10 ש\"ח. הטבות: מניות, גישה מוקדמת + בונוסים לגדולים.", reply_markup=InlineKeyboardMarkup(invest_keyboard))
    elif data == "admin":
        if user and user.is_admin:
            admin_keyboard = [
                [InlineKeyboardButton("עדכן תוכן", callback_data="admin_update_content")],
                [InlineKeyboardButton("הוסף קישור", callback_data="admin_add_link")],
                [InlineKeyboardButton("נהל משתמשים", callback_data="admin_manage_users")],
                [InlineKeyboardButton("אשר תשלומים", callback_data="admin_approve_payments")],
                [InlineKeyboardButton("שנה סיסמה", callback_data="admin_change_pass")],
            ]
            await query.edit_message_text("פאנל אדמין", reply_markup=InlineKeyboardMarkup(admin_keyboard))
        else:
            await query.answer("אין גישה. בקש אישור ממני.")
    elif data == "invest_now":
        await query.answer()
        await query.message.reply_text("שלח סכום השקעה ופרטים. אישור יגיע בקבוצת תשלומים.")
    elif data == "invest_panel":
        # Show user transactions
        transactions = user.transactions
        text = "פאנל משקיע: \n" + "\n".join([f"עסקה {t.id}: {t.amount} ש\"ח, סטטוס: {t.status}, חוזה: {t.contract_hash}" for t in transactions])
        await query.edit_message_text(text)
        await query.message.reply_text("המערכת יוצרת חוזים חכמים, קבלות, כרטיסי ביקור, וזהות NFT להצפנת נכסים.")
    # Add handlers for admin callbacks: e.g., update_content prompts for message, add_link etc.
    # For add_portfolio: /add_portfolio title description links

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = next(get_db())):
    # Handle payments: if in payment group, forward to admin
    if update.message.chat_id == PAYMENT_GROUP_ID:
        # Notify admins
        await context.bot.send_message(ADMIN_USER_ID, f"אישור תשלום חדש: {update.message.text}")
    # Other logic: e.g., if awaiting input for admin update, process it

async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = next(get_db())):
    user = get_user_by_telegram_id(db, update.effective_user.id)
    if user and user.is_admin:
        password = ' '.join(context.args)
        if verify_password(password, user.password_hash):
            if user.active_sessions < 2:
                user.active_sessions += 1
                db.commit()
                await update.message.reply_text("התחברת כאדמין.")
            else:
                await update.message.reply_text("מגבלת 2 מכשירים. בקש אישור ליותר.")
        else:
            await update.message.reply_text("סיסמה שגויה.")
    else:
        await update.message.reply_text("אין גישה.")

# Add /request_lesson, /add_admin (only for you), /approve_payment (update transaction status, send to user/group), etc.
# For logout: decrement active_sessions
