import logging
import random
import os
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler, CallbackQueryHandler, MessageHandler, 
    filters, ContextTypes, Application
)
from telegram.error import TelegramError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.crud import (
    get_user_by_telegram_id, create_user, make_admin, 
    get_user_transactions, update_user
)
from app.schemas import UserCreate

# לוגים
logger = logging.getLogger(__name__)

# קונפיגורציה דרך משתני סביבה
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", 0))
COMMUNITY_GROUP_ID = os.environ.get("COMMUNITY_GROUP_ID", "-1001748319682")
DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD", "secure_admin_password_123")
SITE_URL = "https://osifeu-prog.github.io/PROMO/"

# קישורים מוגדרים מראש - ללא GitHub
LINKS = [
    {"title": "🤖 Slh_selha_bot", "url": "https://t.me/Slh_selha_bot"},
    {"title": "🛒 BUY_MY_SHOP", "url": "https://t.me/BUY_MY_SHOP"},
    {"title": "🎮 NFTY_madness_bot", "url": "https://t.me/NFTY_madness_bot"},
    {"title": "👥 קבוצת קהילה", "url": "https://t.me/+HIzvM8sEgh1kNWY0"},
    {"title": "₿ crypto_A_bot", "url": "https://t.me/crypto_A_bot"},
    {"title": "🎓 SLH_Academia_bot", "url": "https://t.me/SLH_Academia_bot"},
    {"title": "🌐 אתר SLH", "url": SITE_URL},
]

# תמונות רנדומליות
EYE_CATCHING_IMAGES = [
    "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1621417201921-5d9a8f8f9e3d?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1605902711622-cfb43c4437b5?auto=format&fit=crop&w=1200&q=80",
]

# Enum ל-callbacks
class Callback(str):
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
        # Command handlers
        ptb.add_handler(CommandHandler("start", start))
        ptb.add_handler(CommandHandler("login", admin_login))
        ptb.add_handler(CommandHandler("request_admin", request_admin_command))
        ptb.add_handler(CommandHandler("stats", user_stats))
        
        # FIXED: Callback handler with pattern to catch all callbacks
        ptb.add_handler(CallbackQueryHandler(handle_callback, pattern=".*"))
        
        # Message handler
        ptb.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("✅ Bot handlers setup completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to setup bot handlers: {e}")
        raise

def build_main_menu(user: Any = None) -> InlineKeyboardMarkup:
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
    if user and user.is_admin:
        keyboard.append([InlineKeyboardButton("🔒 פאנל אדמין", callback_data=Callback.ADMIN)])
    else:
        keyboard.append([InlineKeyboardButton("🛡️ בקש גישה אדמין", callback_data=Callback.REQUEST_ADMIN)])
    
    return InlineKeyboardMarkup(keyboard)

def build_back_button() -> InlineKeyboardMarkup:
    """כפתור חזרה לתפריט ראשי"""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 חזרה לתפריט הראשי", callback_data=Callback.BACK_TO_MAIN)
    ]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler לפקודת /start"""
    db = None
    try:
        db = SessionLocal()
        user_id = update.effective_user.id
        username = update.effective_user.username
        first_name = update.effective_user.first_name
        
        logger.info(f"🚀 User {user_id} started the bot - @{username} - {first_name}")
        
        # שליחה לוג לקבוצה
        if COMMUNITY_GROUP_ID:
            try:
                log_message = f"👤 משתמש חדש התחיל את הבוט:\nID: {user_id}\nשם: {first_name}\n@{username if username else 'ללא username'}"
                await context.bot.send_message(COMMUNITY_GROUP_ID, log_message)
            except Exception as e:
                logger.error(f"Failed to send log to group: {e}")
        
        # בדיקה או יצירת משתמש
        user = get_user_by_telegram_id(db, user_id)
        if not user:
            user_data = UserCreate(
                telegram_id=user_id,
                username=username,
                first_name=first_name
            )
            user = create_user(db, user_data)
            if user:
                logger.info(f"✅ Created new user: {user_id}")
            else:
                logger.error(f"❌ Failed to create user: {user_id}")
                user = get_user_by_telegram_id(db, user_id)  # Try to get again
        
        # הפיכה לאדמין אם זה המשתמש המוגדר
        if user and user_id == ADMIN_USER_ID and not user.is_admin:
            make_admin(db, user_id, DEFAULT_ADMIN_PASSWORD)
            logger.info(f"👑 User {user_id} promoted to admin")
        
        # שליחת תמונה עם כיתוב
        image_url = random.choice(EYE_CATCHING_IMAGES)
        welcome_text = f"""🚀 *ברוך הבא {first_name or 'חבר'}!*

*הצטרפו למהפכה הדיגיטלית של SLH - אקוסיסטם AI מבוסס אמון!*

✨ *מה תמצאו כאן:*
• פלטפורמת השקעות מתקדמת
• מערכת מסחר ובוטים חכמים  
• אקדמיה דיגיטלית למומחים
• קהילה פעילה של משקיעים

*התחל לגלות את ההזדמנויות!*"""
        
        try:
            await update.message.reply_photo(
                photo=image_url, 
                caption=welcome_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f"Could not send photo: {e}")
            await update.message.reply_text(welcome_text, parse_mode='Markdown')
        
        # שליחת הודעה עם תפריט
        menu_text = "🎯 *בחר את האזור שמעניין אותך:*"
        await update.message.reply_text(
            menu_text, 
            reply_markup=build_main_menu(user),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"❌ Error in start handler: {e}")
        try:
            await update.message.reply_text(
                "❌ אירעה שגיאה בהפעלת הבוט. נסה שוב מאוחר יותר.",
                reply_markup=build_main_menu()
            )
        except Exception as send_error:
            logger.error(f"Could not send error message: {send_error}")
    finally:
        if db:
            db.close()

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler לכל ה-callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    # DEBUG: Log callback details
    logger.info(f"🔄 Callback received: {data} from user {user_id}")
    
    db = None
    try:
        db = SessionLocal()
        user = get_user_by_telegram_id(db, user_id)
        
        # מיפוי handlers ל-callbacks
        if data == Callback.ABOUT:
            await handle_about(query)
        elif data == Callback.CONTENT:
            await handle_content(query)
        elif data == Callback.COINS:
            await handle_coins(query)
        elif data == Callback.GAMES:
            await handle_games(query)
        elif data == Callback.EXPERTS:
            await handle_experts(query)
        elif data == Callback.INVEST:
            await handle_invest(query)
        elif data == Callback.INVEST_NOW:
            await handle_invest_now(query)
        elif data == Callback.INVEST_PANEL:
            await handle_invest_panel(query, db, user)
        elif data == Callback.ADMIN:
            await handle_admin(query, db, user)
        elif data == Callback.REQUEST_ADMIN:
            await handle_request_admin(query, context, db, user)
        elif data == Callback.BACK_TO_MAIN:
            await handle_back_to_main(query, db, user)
        else:
            logger.warning(f"Unknown callback data: {data}")
            await query.edit_message_text(
                "❌ פעולה לא זוהתה.",
                reply_markup=build_back_button()
            )
            
    except Exception as e:
        logger.error(f"❌ Error in callback handler: {e}")
        try:
            await query.edit_message_text(
                "❌ אירעה שגיאה בעיבוד הבקשה.",
                reply_markup=build_back_button()
            )
        except Exception:
            try:
                await query.message.reply_text(
                    "❌ אירעה שגיאה בעיבוד הבקשה.",
                    reply_markup=build_back_button()
                )
            except Exception:
                logger.error("Could not send error message to user")
    finally:
        if db:
            db.close()

# ... (כל שאר פונקציות ה-handle_* נשארות כפי שהיו)

async def handle_about(query):
    """טיפול באודות"""
    try:
        about_text = """
🌟 *אודות SLH - Smart Life Hub*

*המהפכה הדיגיטלית שכולם מדברים עליה!*

🚀 **מה אנחנו?**
אקוסיסטם דיגיטלי חדשני המשלב טכנולוגיות מתקדמות:

📊 *פלטפורמת השקעות מתקדמת*
• השקעות מ-10,000 ש"ח עם תשואות משמעותיות
• שקיפות מלאה וניהול סיכונים חכם
• חוזים דיגיטליים מאובטחים

🤖 *בינה מלאכותית וטכנולוגיה*
• מערכות AI לניתוח שווקים
• בוטים אוטומטיים למסחר
• ניהול תיקים חכם

🎓 *אקדמיה דיגיטלית*
• קורסים מקצועיים במימון וטכנולוגיה
• ליווי אישי ממומחים
• קהילת למידה פעילה

🔗 *בלוקצ'יין ונכסים דיגיטליים*
• מסחר במטבעות קריפטו
• טכנולוגיות Web3 מתקדמות
• פתרונות אבטחה מתקדמים

*הצטרפו אלינו היום ובנו את העתיד הפיננסי שלכם!*"""
        
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

# ... (כל שאר הפונקציות נשארות ללא שינוי)

async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """התחברות כאדמין"""
    db = None
    try:
        db = SessionLocal()
        user_id = update.effective_user.id
        user = get_user_by_telegram_id(db, user_id)
        
        if not user or not user.is_admin:
            await update.message.reply_text("❌ אין לך הרשאות אדמין.")
            return
        
        await update.message.reply_text(
            "🔒 אתה מחובר כאדמין. גש לפאנל הניהול דרך התפריט הראשי.",
            reply_markup=build_main_menu(user)
        )
        
    except Exception as e:
        logger.error(f"Error in admin_login: {e}")
        await update.message.reply_text("❌ שגיאה בהתחברות.")
    finally:
        if db:
            db.close()

async def request_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """פקודה לבקשת אדמין"""
    db = None
    try:
        db = SessionLocal()
        user_id = update.effective_user.id
        user = get_user_by_telegram_id(db, user_id)
        
        if not user:
            user_data = UserCreate(
                telegram_id=user_id, 
                username=update.effective_user.username,
                first_name=update.effective_user.first_name
            )
            user = create_user(db, user_data)
        
        text = """
🛡️ *בקשת גישת אדמין*

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
    finally:
        if db:
            db.close()

async def user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """סטטיסטיקות אישיות"""
    db = None
    try:
        db = SessionLocal()
        user_id = update.effective_user.id
        user = get_user_by_telegram_id(db, user_id)
        
        if not user:
            await update.message.reply_text("❌ לא נמצאו נתונים למשתמש זה.")
            return
        
        transactions = get_user_transactions(db, user.id, limit=5)
        
        text = f"""
📊 *סטטיסטיקות אישיות - {user.first_name or user.username}*

👤 *פרטים:*
• 🆔 ID: {user.telegram_id}
• 📛 שם: {user.first_name or 'לא צוין'}
• 👑 אדמין: {'✅ כן' if user.is_admin else '❌ לא'}
• 📅 הצטרף: {user.created_at.strftime('%d/%m/%Y') if user.created_at else 'לא ידוע'}

💼 *השקעות:*
• 📈 עסקאות: {len(transactions)}
• 🟢 סטטוס פעיל: {'✅' if user.active_sessions > 0 else '❌'}
"""
        
        if transactions:
            text += "\n🔸 *עסקאות אחרונות:*\n"
            for trans in transactions:
                status_emoji = "✅" if trans.status == 'completed' else "⏳" if trans.status == 'pending' else "❌"
                text += f"• {status_emoji} {trans.amount} {trans.currency} - {trans.status}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in user_stats: {e}")
        await update.message.reply_text("❌ שגיאה בטעינת הסטטיסטיקות.")
    finally:
        if db:
            db.close()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler להודעות טקסט רגילות"""
    db = None
    try:
        message_text = update.message.text
        user_id = update.effective_user.id
        
        logger.info(f"💬 Message from user {user_id}: {message_text}")
        
        # תשובה להודעות כלליות
        response = "🤖 *אני בוט SLH!* השתמשו בתפריט או בפקודות לניווט."
        
        db = SessionLocal()
        user = get_user_by_telegram_id(db, user_id)
        
        await update.message.reply_text(
            response, 
            reply_markup=build_main_menu(user),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in message_handler: {e}")
    finally:
        if db:
            db.close()
