import logging
import random
import os
from pathlib import Path
from enum import Enum
from typing import Dict, Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler, CallbackQueryHandler, MessageHandler, 
    filters, ContextTypes, Application
)
from telegram.error import TelegramError
from sqlalchemy.orm import Session

from app.database import get_db
from app.crud import (
    get_user_by_telegram_id, create_user, make_admin, 
    create_portfolio, create_transaction, get_user_transactions,
    update_user
)
from app.schemas import UserCreate, PortfolioCreate

# לוגים
logger = logging.getLogger(__name__)

# קונפיגורציה דרך משתני סביבה
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", 0))
PAYMENT_GROUP_ID = int(os.environ.get("PAYMENT_GROUP_ID", 0))
COMMUNITY_GROUP_ID = int(os.environ.get("COMMUNITY_GROUP_ID", 0))
DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD", "secure_admin_password_123")

# קישורים מוגדרים מראש
LINKS = [
    {"title": "Slh_selha_bot", "url": "https://t.me/Slh_selha_bot"},
    {"title": "BUY_MY_SHOP", "url": "https://t.me/BUY_MY_SHOP"},
    {"title": "NFTY_madness_bot", "url": "https://t.me/NFTY_madness_bot"},
    {"title": "קבוצת קהילת הבורסה", "url": "https://t.me/+HIzvM8sEgh1kNWY0"},
    {"title": "crypto_A_bot", "url": "https://t.me/crypto_A_bot"},
    {"title": "SLH_Academia_bot", "url": "https://t.me/SLH_Academia_bot"},
    {"title": "YouTube Channel", "url": "https://www.youtube.com/channel/UC..."},
]

# תמונות רנדומליות
EYE_CATCHING_IMAGES = [
    "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1621417201921-5d9a8f8f9e3d?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1605902711622-cfb43c4437b5?auto=format&fit=crop&w=1200&q=80",
]

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
    BACK_TO_MAIN = "back_to_main"

def setup_handlers(ptb: Application) -> None:
    """הגדרת כל ה-handlers של הבוט"""
    try:
        ptb.add_handler(CommandHandler("start", start))
        ptb.add_handler(CommandHandler("login", admin_login))
        ptb.add_handler(CommandHandler("request_admin", request_admin_command))
        ptb.add_handler(CommandHandler("stats", user_stats))
        ptb.add_handler(CallbackQueryHandler(callback_handler))
        ptb.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        
        # Error handler
        ptb.add_error_handler(error_handler)
        
        logger.info("Bot handlers setup completed successfully")
    except Exception as e:
        logger.error(f"Failed to setup bot handlers: {e}")
        raise

def build_main_menu() -> InlineKeyboardMarkup:
    """בניית תפריט ראשי"""
    keyboard = [
        [InlineKeyboardButton("🌐 אודות הפרויקט", callback_data=Callback.ABOUT)],
        [InlineKeyboardButton("📚 תוכן ואקדמיה", callback_data=Callback.CONTENT)],
        [InlineKeyboardButton("💰 מטבעות ומסחר", callback_data=Callback.COINS)],
        [InlineKeyboardButton("🎮 משחקים ו-NFT", callback_data=Callback.GAMES)],
        [InlineKeyboardButton("🧑‍💼 מערכת מומחים", callback_data=Callback.EXPERTS)],
        [InlineKeyboardButton("📈 השקעות כבדות", callback_data=Callback.INVEST)],
    ]
    
    # כפתורי אדמין - מוצגים רק למנהלים
    admin_buttons = [
        InlineKeyboardButton("🔒 פאנל אדמין", callback_data=Callback.ADMIN),
        InlineKeyboardButton("🛡️ בקש גישה אדמין", callback_data=Callback.REQUEST_ADMIN),
    ]
    
    keyboard.append(admin_buttons)
    
    return InlineKeyboardMarkup(keyboard)

def build_back_button() -> InlineKeyboardMarkup:
    """כפתור חזרה לתפריט ראשי"""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 חזרה לתפריט הראשי", callback_data=Callback.BACK_TO_MAIN)
    ]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler לפקודת /start"""
    try:
        db = next(get_db())
        user_id = update.effective_user.id
        username = update.effective_user.username
        first_name = update.effective_user.first_name
        
        logger.info(f"User {user_id} started the bot")
        
        # בדיקה או יצירת משתמש
        user = get_user_by_telegram_id(db, user_id)
        if not user:
            user_data = UserCreate(
                telegram_id=user_id,
                username=username,
                first_name=first_name
            )
            user = create_user(db, user_data)
            logger.info(f"Created new user: {user_id}")
        
        # הפיכה לאדמין אם זה המשתמש המוגדר
        if user_id == ADMIN_USER_ID and not user.is_admin:
            make_admin(db, user_id, DEFAULT_ADMIN_PASSWORD)
            logger.info(f"User {user_id} promoted to admin")
        
        # שליחת תמונה עם כיתוב
        image_url = random.choice(EYE_CATCHING_IMAGES)
        welcome_text = f"🚀 ברוך הבא {first_name or 'חבר'}! הצטרפו למהפכה הדיגיטלית של SLH 🚀"
        
        try:
            await update.message.reply_photo(
                photo=image_url, 
                caption=welcome_text
            )
        except TelegramError as e:
            logger.warning(f"Could not send photo: {e}")
            await update.message.reply_text(welcome_text)
        
        # שליחת הודעה עם תפריט
        menu_text = "גלה את העתיד הכלכלי: SLH – אקוסיסטם AI מבוסס אמון!"
        await update.message.reply_text(menu_text, reply_markup=build_main_menu())
        
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await update.message.reply_text(
            "❌ אירעה שגיאה בהפעלת הבוט. נסה שוב מאוחר יותר.",
            reply_markup=build_main_menu()
        )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler לכל ה-callbacks"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        logger.debug(f"Callback received: {data} from user {user_id}")
        
        db = next(get_db())
        user = get_user_by_telegram_id(db, user_id)
        
        handlers = {
            Callback.ABOUT: handle_about,
            Callback.CONTENT: handle_content,
            Callback.COINS: handle_coins,
            Callback.GAMES: handle_games,
            Callback.EXPERTS: handle_experts,
            Callback.INVEST: handle_invest,
            Callback.INVEST_NOW: handle_invest_now,
            Callback.INVEST_PANEL: handle_invest_panel,
            Callback.ADMIN: handle_admin,
            Callback.REQUEST_ADMIN: handle_request_admin,
            Callback.BACK_TO_MAIN: handle_back_to_main,
        }
        
        handler = handlers.get(data)
        if handler:
            await handler(query, context, db, user)
        else:
            await query.edit_message_text(
                "❌ פעולה לא זוהתה.",
                reply_markup=build_back_button()
            )
            
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
        try:
            await query.edit_message_text(
                "❌ אירעה שגיאה בעיבוד הבקשה.",
                reply_markup=build_back_button()
            )
        except:
            pass

async def handle_about(query, context, db, user):
    """טיפול באודות"""
    try:
        about_text = """
        🌐 **אודות SLH - Smart Life Hub**
        
        אקוסיסטם דיגיטלי מבוסס AI המשלב:
        • 📚 אקדמיה לפיננסים וכלכלה
        • 💰 מסחר ומטבעות דיגיטליים
        • 🎮 משחקי NFT וארקייד
        • 🤖 מערכת מומחים חכמה
        • 📈 פלטפורמת השקעות מתקדמת
        
        הצטרפו למהפכה הכלכלית!
        """
        
        await query.edit_message_text(
            about_text,
            reply_markup=build_back_button(),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in handle_about: {e}")
        await query.edit_message_text(
            "❌ שגיאה בטעינת תוכן האודות.",
            reply_markup=build_back_button()
        )

async def handle_content(query, context, db, user):
    """טיפול בתוכן ואקדמיה"""
    text = """
    📚 **תוכן ואקדמיה SLH**
    
    קורסים מקוונים מתקדמים בתחומים:
    • כלכלה בריאה וניהול הון
    • בינה מלאכותית וטכנולוגיה
    • פסיכולוגיה פיננסית
    • מסחר דיגיטלי
    
    🎓 למידה אינטראקטיבית עם מומחים!
    """
    await query.edit_message_text(text, reply_markup=build_back_button(), parse_mode='Markdown')

async def handle_coins(query, context, db, user):
    """טיפול במטבעות ומסחר"""
    text = """
    💰 **מטבעות SLH**
    
    מערכת מטבעות מתקדמת הכוללת:
    • מטבע פנימי עם סטייקינג
    • חיבור ל-Binance Smart Chain
    • אינטגרציה עם TON Blockchain
    • בורסה פנימית למסחר
    
    🚀 השקעה וצמיחה מתמדת!
    """
    await query.edit_message_text(text, reply_markup=build_back_button(), parse_mode='Markdown')

async def handle_games(query, context, db, user):
    """טיפול במשחקים ו-NFT"""
    text = """
    🎮 **משחקים ו-NFT**
    
    אקוסיסטם גיימינג עשיר:
    • תשתית ארקייד מתקדמת
    • קזינו נקודות וחוויה
    • שוק NFT פעיל
    • תחרויות ופרסים
    
    🏆 שחק והרוויח!
    """
    await query.edit_message_text(text, reply_markup=build_back_button(), parse_mode='Markdown')

async def handle_experts(query, context, db, user):
    """טיפול במערכת מומחים"""
    text = """
    🧑‍💼 **מערכת מומחים**
    
    AI חכם לבחירת שותפים:
    • התאמה מקצועית למנטורים
    • ניתוח יכולות וכישורים
    • בניית צוותים אופטימליים
    • ליווי אישי להצלחה
    
    🤝 מצא את השותף המושלם!
    """
    await query.edit_message_text(text, reply_markup=build_back_button(), parse_mode='Markdown')

async def handle_invest(query, context, db, user):
    """טיפול בהשקעות"""
    keyboard = [
        [InlineKeyboardButton(link['title'], url=link['url']) for link in LINKS[:3]],
        [InlineKeyboardButton("השקע עכשיו (מ-10,000 ש\"ח)", callback_data=Callback.INVEST_NOW)],
        [InlineKeyboardButton("פאנל השקעות VIP", callback_data=Callback.INVEST_PANEL)],
        [InlineKeyboardButton("🔙 חזרה", callback_data=Callback.BACK_TO_MAIN)],
    ]
    
    text = """
    📈 **השקעות כבדות**
    
    תוכנית גיוס 10 מיליון ש"ח עם:
    • דיבידנטים ושותפות מלאה
    • שקיפות מלאה בעסקאות
    • חוזים חכמים מאובטחים
    • ליווי צמוד להשקעה
    
    💼 השקיעו בעתיד הדיגיטלי!
    """
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_invest_now(query, context, db, user):
    """טיפול בבקשת השקעה"""
    text = """
    💼 **השקעה כבדה - צור קשר**
    
    לפרטים והשקעה (מ-10,000 ש"ח):
    1. שלחו סכום ופרטים אישיים
    2. קבלו אישור חוזה חכם
    3. הצטרפו לקבוצת התשלומים
    4. התחילו לקבל דיבידנטים
    
    📞 לפניה: @ICQ2_bot
    """
    await query.edit_message_text(text, reply_markup=build_back_button(), parse_mode='Markdown')

async def handle_invest_panel(query, context, db, user):
    """פאנל השקעות אישי"""
    if not user:
        await query.edit_message_text(
            "❌ לא נמצאו נתוני משתמש.",
            reply_markup=build_back_button()
        )
        return
    
    transactions = get_user_transactions(db, user.id, limit=10)
    
    if transactions:
        text = "💼 **פאנל השקעות VIP**\n\n"
        for i, transaction in enumerate(transactions, 1):
            text += f"{i}. עסקה #{transaction.id}: {transaction.amount} ש\"ח\n"
            text += f"   סטטוס: {transaction.status}\n"
            text += f"   תאריך: {transaction.timestamp.strftime('%d/%m/%Y')}\n\n"
    else:
        text = "💼 **פאנל השקעות VIP**\n\nאין עסקאות כרגע.\n\nהתחל להשקיע עכשיו!"
    
    await query.edit_message_text(text, reply_markup=build_back_button(), parse_mode='Markdown')

async def handle_admin(query, context, db, user):
    """פאנל אדמין"""
    if not user or not user.is_admin:
        await query.answer("❌ גישה מוגבלת - אין לך הרשאות אדמין.", show_alert=True)
        return
    
    text = """
    🔒 **פאנל אדמין מתקדם**
    
    ניהול מלא של אקוסיסטם SLH:
    • עדכון תוכן והגדרות
    • ניהול משתמשים והרשאות
    • אישור השקעות ועסקאות
    • דוחות וסטטיסטיקות
    
    🛠️ פונקציות ניהול זמינות דרך הפקודות.
    """
    
    await query.edit_message_text(text, reply_markup=build_back_button(), parse_mode='Markdown')

async def handle_request_admin(query, context, db, user):
    """בקשת הרשאות אדמין"""
    text = """
    🛡️ **בקשת גישת אדמין**
    
    בקשתך נשלחה להתייחסות.
    נציג יחזור אליך בהקדם לדיון
    בחוזה חכם והגדרת הרשאות.
    
    📧 לדיון מהיר: @ICQ2_bot
    """
    
    try:
        if COMMUNITY_GROUP_ID:
            admin_message = f"🛡️ בקשת אדמין חדשה מ-@{user.username or 'Unknown'} (ID: {user.telegram_id})"
            await context.bot.send_message(COMMUNITY_GROUP_ID, admin_message)
    except Exception as e:
        logger.error(f"Could not send admin request to group: {e}")
    
    await query.edit_message_text(text, reply_markup=build_back_button(), parse_mode='Markdown')

async def handle_back_to_main(query, context, db, user):
    """חזרה לתפריט ראשי"""
    await query.edit_message_text(
        "גלה את העתיד הכלכלי: SLH – אקוסיסטם AI מבוסס אמון!",
        reply_markup=build_main_menu()
    )

async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """התחברות כאדמין"""
    try:
        db = next(get_db())
        user_id = update.effective_user.id
        user = get_user_by_telegram_id(db, user_id)
        
        if not user or not user.is_admin:
            await update.message.reply_text("❌ אין לך הרשאות אדמין.")
            return
        
        await update.message.reply_text(
            "🔒 אתה מחובר כאדמין. גש לפאנל הניהול דרך התפריט הראשי.",
            reply_markup=build_main_menu()
        )
        
    except Exception as e:
        logger.error(f"Error in admin_login: {e}")
        await update.message.reply_text("❌ שגיאה בהתחברות.")

async def request_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """פקודה לבקשת אדמין"""
    try:
        db = next(get_db())
        user_id = update.effective_user.id
        user = get_user_by_telegram_id(db, user_id)
        
        if not user:
            user_data = UserCreate(telegram_id=user_id, username=update.effective_user.username)
            user = create_user(db, user_data)
        
        text = """
        🛡️ **בקשת גישת אדמין**
        
        בקשתך נשלחה להתייחסות.
        נציג יחזור אליך בהקדם לדיון
        בחוזה חכם והגדרת הרשאות.
        
        📧 לדיון מהיר: @ICQ2_bot
        """
        
        try:
            if COMMUNITY_GROUP_ID:
                admin_message = f"🛡️ בקשת אדמין חדשה מ-@{user.username or 'Unknown'} (ID: {user.telegram_id})"
                await context.bot.send_message(COMMUNITY_GROUP_ID, admin_message)
        except Exception as e:
            logger.error(f"Could not send admin request to group: {e}")
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in request_admin_command: {e}")
        await update.message.reply_text("❌ שגיאה בשליחת הבקשה.")

async def user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """סטטיסטיקות אישיות"""
    try:
        db = next(get_db())
        user_id = update.effective_user.id
        user = get_user_by_telegram_id(db, user_id)
        
        if not user:
            await update.message.reply_text("❌ לא נמצאו נתונים למשתמש זה.")
            return
        
        transactions = get_user_transactions(db, user.id, limit=5)
        
        text = f"""
        📊 **סטטיסטיקות אישיות - {user.first_name or user.username}**
        
        👤 פרטים:
        • ID: {user.telegram_id}
        • שם: {user.first_name or 'לא צוין'}
        • אדמין: {'✅ כן' if user.is_admin else '❌ לא'}
        
        💼 השקעות:
        • עסקאות: {len(transactions)}
        • סטטוס פעיל: {'✅' if user.active_sessions > 0 else '❌'}
        """
        
        if transactions:
            text += "\n🔸 עסקאות אחרונות:\n"
            for trans in transactions:
                text += f"• {trans.amount} ש\"ח - {trans.status}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in user_stats: {e}")
        await update.message.reply_text("❌ שגיאה בטעינת הסטטיסטיקות.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler להודעות טקסט רגילות"""
    try:
        message_text = update.message.text
        user_id = update.effective_user.id
        chat_id = update.message.chat_id
        
        logger.info(f"Message from user {user_id}: {message_text}")
        
        # טיפול בהודעות בקבוצת תשלומים
        if chat_id == PAYMENT_GROUP_ID:
            await handle_payment_group_message(update, context)
            return
        
        # תשובה להודעות כלליות
        response = "🤖 אני בוט SLH! השתמשו בתפריט או בפקודות לניווט."
        await update.message.reply_text(response, reply_markup=build_main_menu())
        
    except Exception as e:
        logger.error(f"Error in message_handler: {e}")

async def handle_payment_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """טיפול בהודעות בקבוצת תשלומים"""
    try:
        message = update.message
        text = message.text
        
        # כאן ניתן להוסיף לוגיקה לזיהוי תשלומים
        # לדוגמה: זיהוי סכומים, אישורי תשלום, etc.
        
        if any(word in text.lower() for word in ['שולם', 'אושר', 'תשלום', 'payment']):
            # שליחה לאדמין להתייחסות
            if ADMIN_USER_ID:
                admin_alert = f"💰 הודעה חדשה בקבוצת תשלומים:\n\n{text}"
                await context.bot.send_message(ADMIN_USER_ID, admin_alert)
                
    except Exception as e:
        logger.error(f"Error handling payment group message: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """טיפול בשגיאות כלליות"""
    try:
        logger.error(f"Exception while handling an update: {context.error}")
        
        # שליחת הודעת שגיאה למשתמש
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ אירעה שגיאה בעיבוד הבקשה. נסה שוב מאוחר יותר.",
                reply_markup=build_main_menu()
            )
    except Exception as e:
        logger.error(f"Error in error_handler: {e}")
