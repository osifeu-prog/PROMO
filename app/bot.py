from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.orm import Session
from app.database import get_db
from app.crud import get_user_by_telegram_id, create_user, make_admin, create_portfolio, create_transaction
from app.utils import verify_password
from app.models import Link
from app.schemas import UserCreate, PortfolioCreate
import os
import random  # For random image if needed

ADMIN_USER_ID = int(os.environ['ADMIN_USER_ID'])
PAYMENT_GROUP_ID = int(os.environ['PAYMENT_GROUP_ID'])
COMMUNITY_GROUP_ID = int(os.environ['COMMUNITY_GROUP_ID'])
SITE_URL = "https://yourusername.github.io/repo/"  # Update to your GitHub Pages URL

# Predefined links
LINKS = [
    {"title": "Slh_selha_bot", "url": "https://t.me/Slh_selha_bot"},
    {"title": "BUY_MY_SHOP", "url": "https://t.me/BUY_MY_SHOP"},
    {"title": "NFTY_madness_bot", "url": "https://t.me/NFTY_madness_bot"},
    {"title": "קבוצת קהילת הבורסה", "url": "https://t.me/+HIzvM8sEgh1kNWY0"},
    {"title": "crypto_A_bot", "url": "https://t.me/crypto_A_bot"},
    {"title": "אתר ראשי: SLH", "url": SITE_URL},
    {"title": "SLH_Academia_bot", "url": "https://t.me/SLH_Academia_bot"},
    {"title": "YouTube Channel", "url": "https://www.youtube.com/channel/UC..."},  # Add full URL
]

# Eye-catching images (random selection - valid URL for Telegram)
EYE_CATCHING_IMAGES = [
    "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?ixlib=rb-4.0.3&auto=format&fit=crop&w=1200&q=80",  # AI and crypto image from Unsplash (reliable)
    # Add more if needed
]

ABOUT_TEXT = """
🌟 **SLH Ecosystem — Investor Overview 2025** 🌟
The Next-Generation Financial, Commercial & Social Economic Engine
Built on Blockchain, AI, and Human Capital Protocol

1. Executive Summary
SLH Ecosystem הוא אקו־סיסטם חדשני המאחד: ✓ פלטפורמות מסחר ✓ ארנק קריפטו חוצה-רשתות (BSC & TON) ✓ מערכת תשלומים קהילתית ✓ חנות בוטים דיגיטלית אוטומטית ✓ אקדמיה למומחים עם תגמול אמיתי ✓ מערכת נקודות Pi Index הדומה ל-Pi Network ✓ עסקאות בנקאיות, NFT, וחוזים חכמים ✓ AI מתמטי ללימוד, ניהול הון, ואוטומציה ✓ תשתית רווח של 39 ש"ח למשתמש חדש
האקו־סיסטם מבוסס על העיקרון: “Knowledge = Capital. Time = Currency.”
המערכת מתגמלת מומחים, בעלי עסקים, מתכנתים ומשתמשים – כולם בתוך כלכלה אחת המאחדת Web2, Web3 ו-AI.

2. Problem SLH Solves
העולם מפוצל ליותר מדי מערכות: * ארנקים שונים (TON/BSC/ETH) * פלטפורמות מסחר נפרדות * קורסים ולמידה ללא מדד או תגמול * עורכי בוטים שונים ללא Marketplace * רשתות חברתיות שלא משתפות רווח עם המשתמשים * חסמי ידע גבוהים * חוסר אמון במודלים מסורתיים
SLH מאחדת הכל למערכת אקולוגית אחת: Blockchain + AI + Automation + Social Economy.

3. The SLH Economic Model
3.1. Multi-Layer Value Engine
1. Community Wallet: ארנק ב-BSC וב-TON המחזיק נכסי קהילה וכל עסקאות המשתמשים.
2. SLH Token Utility: תשלומים, שכר למומחים, Airdrops, אחזקות קהילה, Marketplace, רווחי בוטים, שכר על ידע.
3. Pi Index — Human Capital Protocol: כמו Pi Network → אבל מודל אמיתי: כל אדם צובר נקודות על זמן, למידה, פעילות, פרויקטים. מומחים מקבלים “כח חלוקה” גבוה יותר. המערכת מלמדת את עצמה מי תורם הכי הרבה. ערך המטבע מנוהל לפי פעילות כלכלית אמיתית.
4. E-Commerce Engine (Buy-My-Shop): כל אדם מקבל חנות אישית. מכירות, עמלות, הפניות, מוצרים דיגיטליים, שירותים.
5. AI + Bot Factory: Marketplace לבניית בוטים, תוספים, ותהליכים אוטומטיים.

(המשך כל הסקשנים 4-12 באותו סגנון – הטקסט ארוך, אז חתכתי כאן; הדבק את הכל ב-ABOUT_TEXT בפועל).

הצטרפו לגיוס של 10 מיליון ש"ח – השקעות מ-10,000 ש"ח עם תשואות דיבידנטים, ומעל 100,000 ש"ח – שותפות מלאה!
"""

def setup_handlers(ptb):
    ptb.add_handler(CommandHandler("start", start))
    ptb.add_handler(CommandHandler("login", admin_login))
    ptb.add_handler(CommandHandler("request_admin", request_admin))  # New: for admin requests
    ptb.add_handler(CallbackQueryHandler(callback_handler))
    ptb.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = next(get_db())):
    user_id = update.effective_user.id
    user = get_user_by_telegram_id(db, user_id)
    if not user:
        user = create_user(db, UserCreate(telegram_id=user_id, username=update.effective_user.username))
    if user_id == ADMIN_USER_ID and not user.is_admin:
        make_admin(db, user_id, "admin123")  # Short password

    # Send eye-catching image
    image_url = random.choice(EYE_CATCHING_IMAGES)
    try:
        await update.message.reply_photo(photo=image_url, caption="🚀 הצטרפו למהפכה הדיגיטלית של SLH – אקוסיסטם שווה מיליונים! 🚀")
    except:
        await update.message.reply_text("🚀 הצטרפו למהפכה הדיגיטלית של SLH – אקוסיסטם שווה מיליונים! 🚀")  # Fallback if image fails

    # Advanced menu with enriched text
    keyboard = [
        [InlineKeyboardButton("🌐 אודות הפרויקט", callback_data="about")],
        [InlineKeyboardButton("📚 תוכן ואקדמיה", callback_data="content")],  # Changed from academy/lessons to content
        [InlineKeyboardButton("💰 מטבעות ומסחר", callback_data="coins")],
        [InlineKeyboardButton("🎮 משחקים ו-NFT", callback_data="games")],
        [InlineKeyboardButton("🧑‍💼 מערכת מומחים", callback_data="experts")],
        [InlineKeyboardButton("📈 השקעות כבדות", callback_data="invest")],
        [InlineKeyboardButton("🔗 בקר באתר", url=SITE_URL)],
        [InlineKeyboardButton("🔒 אדמין (מורשים)", callback_data="admin")],
        [InlineKeyboardButton("🛡️ בקש גישה אדמין", callback_data="request_admin")],  # New button
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("גלה את העתיד הכלכלי: SLH – אקוסיסטם AI מבוסס אמון, שווה מיליונים להשקעה!", reply_markup=reply_markup)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = next(get_db())):
    query = update.callback_query
    data = query.data
    user = get_user_by_telegram_id(db, query.from_user.id)
    
    if data == "about":
        await query.edit_message_text(ABOUT_TEXT)  # Full enriched text
    elif data == "content":  # Changed from academy/lessons
        await query.edit_message_text("📚 **תוכן ואקדמיה SLH**: קורסים מקוונים בכלכלה בריאה, AI ופסיכולוגיה. מכירה דיגיטלית עם תגמולים. בקש גישה: /request_content [שם תוכן]")
    elif data == "coins":
        await query.edit_message_text("💰 **מטבעות SLH**: מטבע פנימי עם סטייקינג, חיבור לביננס ו-TON. ערך מבוסס שיתוף – צמיחה מובטחת! חלק מהמודל הכלכלי ששווה מיליונים.")
    elif data == "games":
        await query.edit_message_text("🎮 **משחקים**: תשתית ארקייד, קזינו נקודות ו-NFT. הרוויחו דרך משחקים חברתיים – חלק מהאקוסיסטם הרווחי.")
    elif data == "experts":
        await query.edit_message_text("🧑‍💼 **מערכת מומחים**: AI לבחירת שותפים, מנטורים ועסקאות חכמות. בנו רשת מקצועית – יתרון תחרותי עצום.")
    elif data == "invest":
        invest_keyboard = [
            [InlineKeyboardButton(link['title'], url=link['url']) for link in LINKS[:3]],
            [InlineKeyboardButton("השקע עכשיו (מ-10,000 ש\"ח)", callback_data="invest_now")],
            [InlineKeyboardButton("פאנל השקעות VIP", callback_data="invest_panel")],
        ]
        await query.edit_message_text("📈 **השקעות כבדות**: גיוס 10 מיליון ש\"ח. מ-10,000 ש\"ח – דיבידנטים; מעל 100,000 – שותפות. הטבות: גישה VIP, אחוזים מרווחים. אקוסיסטם שווה מיליונים!", reply_markup=InlineKeyboardMarkup(invest_keyboard))
    elif data == "invest_now":
        await query.message.reply_text("צור קשר להשקעה: שלח סכום (מ-10,000 ש\"ח) ופרטים. אישור חוזה חכם בקבוצת תשלומים – בוא נבנה את העתיד יחד!")
    elif data == "invest_panel":
        transactions = user.transactions
        text = "פאנל השקעות VIP:\n" + "\n".join([f"עסקה {t.id}: {t.amount} ש\"ח, סטטוס: {t.status}" for t in transactions]) + "\nאקוסיסטם SLH – תשואות גבוהות מובטחות!"
        await query.edit_message_text(text)
    elif data == "admin":
        if user and user.is_admin:
            admin_keyboard = [
                [InlineKeyboardButton("עדכן תוכן", callback_data="admin_update")],
                [InlineKeyboardButton("הוסף קישור", callback_data="admin_add_link")],
                [InlineKeyboardButton("נהל משתמשים", callback_data="admin_users")],
                [InlineKeyboardButton("אשר השקעות", callback_data="admin_approve")],
                [InlineKeyboardButton("שנה סיסמה", callback_data="admin_pass")],
            ]
            await query.edit_message_text("פאנל אדמין מתקדם – נהל את האקוסיסטם ששווה מיליונים!", reply_markup=InlineKeyboardMarkup(admin_keyboard))
        else:
            await query.answer("גישה מוגבלת – בקש אישור.")
    elif data == "request_admin":
        await query.message.reply_text("בקשת אדמין נשלחה לקבוצה. נדון בחוזה חכם דרך הבוט – שלח הודעה לקבוצה להתחיל דיון.")

async def request_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(COMMUNITY_GROUP_ID, f"בקשת אדמין חדשה מ-{update.effective_user.username}! נהל דיון וחוזה חכם כאן.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = next(get_db())):
    chat_id = update.message.chat_id
    if chat_id == PAYMENT_GROUP_ID:
        await context.bot.send_message(ADMIN_USER_ID, f"אישור תשלום חדש: {update.message.text}")
    elif chat_id == COMMUNITY_GROUP_ID:  # Handle discussions in community group
        # Forward to admin for contract discussion
        await context.bot.forward_message(ADMIN_USER_ID, chat_id, update.message.message_id)
        await context.bot.send_message(ADMIN_USER_ID, "הגב דרך הבוט לכתיבת חוזה חכם.")
    # Other logic...

async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = next(get_db())):
    # ... (same as before)
