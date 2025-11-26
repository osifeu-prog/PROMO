import logging
import random
import os
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler, CallbackQueryHandler, MessageHandler, 
    filters, ContextTypes, Application
)
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

# קישורים מוגדרים מראש
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
        ptb.add_handler(CommandHandler("start", start))
        ptb.add_handler(CommandHandler("login", admin_login))
        ptb.add_handler(CommandHandler("request_admin", request_admin_command))
        ptb.add_handler(CommandHandler("stats", user_stats))
        ptb.add_handler(CallbackQueryHandler(handle_callback, pattern=".*"))
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
        
        logger.info(f"🚀 User {user_id} started the bot")
        
        # שליחה לוג לקבוצה
        if COMMUNITY_GROUP_ID:
            try:
                log_message = f"👤 משתמש חדש: {first_name} (@{username}) - ID: {user_id}"
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
            logger.info(f"✅ Created new user: {user_id}")
        
        # הפיכה לאדמין אם זה המשתמש המוגדר
        if user_id == ADMIN_USER_ID and not user.is_admin:
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
        await update.message.reply_text(
            "❌ אירעה שגיאה בהפעלת הבוט. נסה שוב מאוחר יותר.",
            reply_markup=build_main_menu()
        )
    finally:
        if db:
            db.close()

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler לכל ה-callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    logger.info(f"🔄 Callback received: {data} from user {user_id}")
    
    db = None
    try:
        db = SessionLocal()
        user = get_user_by_telegram_id(db, user_id)
        
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

async def handle_about(query):
    """טיפול באודות"""
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

async def handle_content(query):
    """טיפול בתוכן ואקדמיה"""
    text = """
📚 *תוכן ואקדמיה SLH*

*קורסים מקוונים מתקדמים בתחומים:*
• כלכלה בריאה וניהול הון
• בינה מלאכותית וטכנולוגיה
• פסיכולוגיה פיננסית
• מסחר דיגיטלי ובלוקצ'יין
• ניהול סיכונים והשקעות

🎓 *יתרונות הלמידה אצלנו:*
• ליווי אישי ממומחים
• תוכן מעודכן ואקטואלי
• קהילת לומדים תומכת
• תעודות הסמכה רשמיות

*הקורסים החדשים יפתחו בקרוב! הישארו מעודכנים.*"""
    
    keyboard = [
        [InlineKeyboardButton("🎓 קורסים קרובים", url="https://t.me/SLH_Academia_bot")],
        [InlineKeyboardButton("📖 חומרי לימוד", url=SITE_URL)],
        [InlineKeyboardButton("🔙 חזרה", callback_data=Callback.BACK_TO_MAIN)]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_coins(query):
    """טיפול במטבעות ומסחר"""
    text = """
💰 *מטבעות SLH - מערכת מסחר מתקדמת*

*הפלטפורמה המשולבת שלנו מציעה:*

🪙 *מטבע פנימי עם סטייקינג*
• תשואות אטרקטיביות על אחזקה
• שימוש במערכת הפנימית
• הטבות בלעדיות למחזיקים

🔗 *חיבור לרשתות מובילות*
• Binance Smart Chain (BSC)
• TON Blockchain
• Ethereum Network
• רשתות נוספות בהמשך

📈 *בורסה פנימית מתקדמת*
• מסחר בזמן אמת
• עמלות תחרותיות
• ממשק מתקדם ופשוט

🤖 *בוט מסחר חכם*
• ניתוחים טכניים מתקדמים
• איתותים אוטומטיים
• ניהול סיכונים חכם

*הצטרפו למהפכת הקריפטו עם SLH!*"""
    
    keyboard = [
        [InlineKeyboardButton("🪙 מטבע SLH", url="https://t.me/crypto_A_bot")],
        [InlineKeyboardButton("📈 בוט מסחר", url="https://t.me/Slh_selha_bot")],
        [InlineKeyboardButton("💱 המרות", url="https://t.me/BUY_MY_SHOP")],
        [InlineKeyboardButton("🔙 חזרה", callback_data=Callback.BACK_TO_MAIN)]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_games(query):
    """טיפול במשחקים ו-NFT"""
    text = """
🎮 *משחקים ו-NFT - חוויה ייחודית*

*אקוסיסטם גיימינג עשיר ומתקדם:*

🎯 *תשתית ארקייד מתקדמת*
• משחקים מרובי משתתפים
• תחרויות עם פרסים
• דירוגים ולידרבורדים

🃏 *קזינו נקודות וחוויה*
• משחקים קלאסיים
• טורנירים שבועיים
• פרסים ומתנות

🖼️ *שוק NFT פעיל*
• יצירה ומכירה של NFT
• תערוכות דיגיטליות
• קולקציות בלעדיות

🏆 *תחרויות ופרסים*
• אירועים שבועיים
• פרסים כספיים
• נכסים דיגיטליים

*שחקו והרוויחו עם SLH Games!*"""
    
    keyboard = [
        [InlineKeyboardButton("🎮 משחקים", url="https://t.me/NFTY_madness_bot")],
        [InlineKeyboardButton("🖼️ NFT", url="https://t.me/BUY_MY_SHOP")],
        [InlineKeyboardButton("🏆 טורנירים", url="https://t.me/+HIzvM8sEgh1kNWY0")],
        [InlineKeyboardButton("🔙 חזרה", callback_data=Callback.BACK_TO_MAIN)]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_experts(query):
    """טיפול במערכת מומחים"""
    text = """
🧑‍💼 *מערכת מומחים - מצאו את השותף המושלם*

*רשת מומחים גלובלית עם AI מתקדם:*

🤝 *התאמה מקצועית*
• אלגוריתם AI חכם להתאמה
• ניתוח יכולות וכישורים
• בניית צוותים אופטימליים

🎯 *ניתוח יכולות מתקדם*
• מיפוי כישורים וניסיון
• התאמה לפרויקטים ספציפיים
• המלצות חכמות

👥 *בניית צוותים אופטימליים*
• הרכב צוותים מאוזן
• השלמת כישורים
• ניהול פרויקטים משותף

📊 *ליווי אישי להצלחה*
• מנטורינג אישי
• פידבקים ובקרה
• פיתוח קריירה

*הצטרפו לקהילת המומחים של SLH!*"""
    
    keyboard = [
        [InlineKeyboardButton("🤖 מערכת מומחים", url="https://t.me/SLH_Academia_bot")],
        [InlineKeyboardButton("👥 קהילה", url="https://t.me/+HIzvM8sEgh1kNWY0")],
        [InlineKeyboardButton("📚 משאבים", url=SITE_URL)],
        [InlineKeyboardButton("🔙 חזרה", callback_data=Callback.BACK_TO_MAIN)]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_invest(query):
    """טיפול בהשקעות"""
    keyboard = [
        [InlineKeyboardButton("📊 מידע השקעות", url=SITE_URL)],
        [InlineKeyboardButton("🤵 צור קשר", url="https://t.me/ICQ2_bot")],
        [InlineKeyboardButton("💼 פאנל השקעות", callback_data=Callback.INVEST_PANEL)],
        [InlineKeyboardButton("💰 השקע עכשיו", callback_data=Callback.INVEST_NOW)],
        [InlineKeyboardButton("🔙 חזרה", callback_data=Callback.BACK_TO_MAIN)],
    ]
    
    text = """
📈 *השקעות כבדות - הזדמנות ייחודית*

*תוכנית גיוס 10 מיליון ש"ח עם יתרונות בלעדיים:*

💎 *דיבידנטים ושותפות מלאה*
• תשואות חודשיות קבועות
• שקיפות מלאה בעסקאות
• שותפות אסטרטגית

🛡️ *שקיפות ואבטחה*
• חוזים חכמים מאובטחים
• ביקורות סדירות
• דוחות כספיים שקופים

🤝 *ליווי צמוד להשקעה*
• ייעוץ מקצועי צמוד
• ניהול סיכונים מתקדם
• עדכונים שוטפים

📊 *מודל השקעה מוכח*
• ניסיון מוכח בשוק
• תיק השקעות מגוון
• אסטרטגיות מותאמות אישית

*השקיעו בעתיד הדיגיטלי עם SLH!*"""
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_invest_now(query):
    """טיפול בבקשת השקעה"""
    text = """
💼 *השקעה כבדה - צרו קשר היום!*

*לפרטים והשקעה (מ-10,000 ש"ח):*

📋 *תהליך ההשקעה:*
1. *שלב ראשון:* צרו קשר והעבירו פרטים
2. *שלב שני:* קבלו הצעת השקעה מותאמת
3. *שלב שלישי:* חתימה על חוזה חכם
4. *שלב רביעי:* העברת השקעה וקבלת אישור
5. *שלב חמישי:* הצטרפות לקבוצת משקיעים בלעדית

🛡️ *יתרונות בלעדיים:*
• ליווי אישי צמוד
• שקיפות מלאה
• דיווחים שוטפים
• תשואות אטרקטיביות

📞 *דרכי יצירת קשר:*
• בוט טלגרם: @ICQ2_bot
• אתר: https://osifeu-prog.github.io/PROMO/
• מייל: info@slh-ecosystem.com

*המהפכה הדיגיטלית מחכה לכם!*"""
    
    await query.edit_message_text(
        text,
        reply_markup=build_back_button(),
        parse_mode='Markdown'
    )

async def handle_invest_panel(query, db, user):
    """פאנל השקעות אישי"""
    if not user:
        await query.edit_message_text(
            "❌ לא נמצאו נתוני משתמש.",
            reply_markup=build_back_button()
        )
        return
    
    transactions = get_user_transactions(db, user.id, limit=10)
    
    text = f"""
💼 *פאנל השקעות VIP - {user.first_name or user.username}*

📊 *סטטוס משתמש:*
• 🤵 משקיע: {user.first_name or 'אורח'}
• 🆔 מזהה: {user.telegram_id}
• 📅 הצטרף: {user.created_at.strftime('%d/%m/%Y') if user.created_at else 'לא ידוע'}

"""
    
    if transactions:
        text += "💰 *עסקאות אחרונות:*\n"
        total_invested = sum(t.amount for t in transactions if t.status == 'completed')
        
        for i, transaction in enumerate(transactions, 1):
            status_emoji = "✅" if transaction.status == 'completed' else "⏳" if transaction.status == 'pending' else "❌"
            text += f"{i}. {status_emoji} *{transaction.amount:,.2f} {transaction.currency}*\n"
            text += f"   📝 {transaction.description or 'השקעה כללית'}\n"
            text += f"   🕒 {transaction.timestamp.strftime('%d/%m/%Y')}\n\n"
        
        text += f"*סך הכל הושקע:* {total_invested:,.2f} {transactions[0].currency if transactions else 'USD'}"
    else:
        text += """
📭 *אין עסקאות כרגע*

💡 *התחל להשקיע עכשיו וקבל:*
• תשואות משמעותיות
• ליווי אישי צמוד
• גישה לקהילה בלעדית

🎯 *להתחלת השקעה:*"""
    
    keyboard = [
        [InlineKeyboardButton("💰 השקע עכשיו", callback_data=Callback.INVEST_NOW)],
        [InlineKeyboardButton("📞 צור קשר", url="https://t.me/ICQ2_bot")],
        [InlineKeyboardButton("🔙 חזרה", callback_data=Callback.BACK_TO_MAIN)]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_admin(query, db, user):
    """פאנל אדמין"""
    if not user or not user.is_admin:
        await query.answer("❌ גישה מוגבלת - אין לך הרשאות אדמין.", show_alert=True)
        return
    
    text = f"""
🔒 *פאנל אדמין מתקדם - {user.first_name or user.username}*

*ניהול מלא של אקוסיסטם SLH:*

📊 *סטטיסטיקות מערכת*
• צפייה בנתונים ועדכונים
• ניתוח ביצועים
• דוחות מתקדמים

👥 *ניהול משתמשים*
• ניהול הרשאות
• סטטיסטיקות משתמשים
• תמיכה וסיוע

📝 *ניהול תוכן*
• הוספת ועדכון תוכן
• ניהול קורסים
• פרסום הודעות

💳 *ניהול עסקאות*
• מעקב אחר השקעות
• אישור עסקאות
• דוחות כספיים

📢 *שליחת הודעות*
• הודעות לקהילה
• עדכונים למשקיעים
• פרסומים שיווקיים

*בחר פעולה לניהול:*"""
    
    await query.edit_message_text(
        text,
        reply_markup=build_back_button(),
        parse_mode='Markdown'
    )

async def handle_request_admin(query, context, db, user):
    """בקשת הרשאות אדמין"""
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
    
    await query.edit_message_text(text, reply_markup=build_back_button(), parse_mode='Markdown')

async def handle_back_to_main(query, db, user):
    """חזרה לתפריט ראשי"""
    await query.edit_message_text(
        "🎯 *בחר את האזור שמעניין אותך:*",
        reply_markup=build_main_menu(user),
        parse_mode='Markdown'
    )

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
