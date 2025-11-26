import os
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from telegram import Update
from telegram.ext import Application
from telegram.error import TelegramError
from sqlalchemy.orm import Session

from app.database import engine, Base, get_db, SessionLocal, create_tables
from app.bot import setup_handlers
from app import crud

# ========= LOGGING SETUP =========

logging.basicConfig(
    level=logging.DEBUG,  # שינוי ל-DEBUG ליותר פרטים
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("app.main")

# ========= CONFIG =========

class Settings:
    def __init__(self):
        self.bot_token = os.getenv("BOT_TOKEN")
        self.webhook_url = os.getenv("WEBHOOK_URL", "").rstrip("/")
        self.environment = os.getenv("ENVIRONMENT", "production")
        
        if not self.bot_token:
            raise ValueError("BOT_TOKEN environment variable is required")
        
        logger.info(f"🔧 Config: BOT_TOKEN={'***' + self.bot_token[-4:] if self.bot_token else 'MISSING'}")
        logger.info(f"🔧 Config: WEBHOOK_URL={self.webhook_url}")

settings = Settings()

# ========= DB INIT =========

def init_db():
    """אתחול מסד הנתונים"""
    try:
        create_tables()
        logger.info("✅ Database tables initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

# ========= TELEGRAM APPLICATION =========

try:
    ptb_app = Application.builder().token(settings.bot_token).build()
    setup_handlers(ptb_app)
    logger.info("✅ Telegram application initialized successfully")
except Exception as e:
    logger.critical(f"❌ Failed to initialize Telegram application: {e}")
    raise

# ========= LIFESPAN =========

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 Starting application in {settings.environment} mode")
    
    try:
        # אתחול מסד נתונים
        init_db()
        
        await ptb_app.initialize()
        logger.info("✅ Telegram application initialized")

        # הגדרת webhook
        if settings.webhook_url:
            hook_url = f"{settings.webhook_url}/{settings.bot_token}"
            try:
                # מחיקת webhook קיים והגדרה מחדש
                logger.info(f"🔄 Deleting existing webhook...")
                await ptb_app.bot.delete_webhook(drop_pending_updates=True)
                time.sleep(2)
                
                logger.info(f"🔄 Setting new webhook to: {hook_url}")
                await ptb_app.bot.set_webhook(
                    url=hook_url,
                    drop_pending_updates=True,
                    allowed_updates=["message", "callback_query", "inline_query"]
                )
                
                # בדיקת webhook
                webhook_info = await ptb_app.bot.get_webhook_info()
                logger.info(f"✅ Webhook info: URL={webhook_info.url}, Pending={webhook_info.pending_update_count}, Has Custom Certificate={webhook_info.has_custom_certificate}")
                
                if webhook_info.url != hook_url:
                    logger.error(f"❌ Webhook URL mismatch! Expected: {hook_url}, Got: {webhook_info.url}")
                else:
                    logger.info("✅ Webhook configured correctly!")
                    
            except TelegramError as e:
                logger.error(f"❌ Failed to set webhook: {e}")
        else:
            logger.warning("⚠️ No WEBHOOK_URL set - using polling")

        await ptb_app.start()
        logger.info("✅ Application startup completed successfully")

    except Exception as e:
        logger.critical(f"❌ Application startup failed: {e}")
        raise

    try:
        yield
    finally:
        logger.info("🛑 Shutting down application...")
        try:
            await ptb_app.stop()
            await ptb_app.shutdown()
            logger.info("✅ Telegram application stopped successfully")
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")

# ========= FASTAPI APP =========

app = FastAPI(
    title="SLH Ecosystem API",
    description="SLH Ecosystem Bot Backend",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ========= MIDDLEWARE =========

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========= ROUTES =========

@app.post(f"/{settings.bot_token}")
async def telegram_webhook(request: Request):
    """נקודת Webhook שמטפלת בכל העדכונים מטלגרם."""
    try:
        # קריאת הגוף של הבקשה
        body = await request.body()
        body_text = body.decode('utf-8')
        
        logger.info(f"📩 Received webhook request")
        logger.debug(f"📦 Request body: {body_text}")
        
        data = json.loads(body_text)
        
        # לוג בסיסי
        update_id = data.get('update_id', 'unknown')
        message_text = data.get('message', {}).get('text', 'No text')
        user_id = data.get('message', {}).get('from', {}).get('id', 'Unknown')
        
        logger.info(f"🔄 Processing update {update_id} from user {user_id}: {message_text}")
        
        # עיבוד העדכון
        update = Update.de_json(data, ptb_app.bot)
        await ptb_app.process_update(update)
        
        logger.info(f"✅ Successfully processed update {update_id}")
        
        return Response(status_code=200, content="OK")
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error: {e}")
        return Response(status_code=400, content="Invalid JSON")
    except Exception as e:
        logger.error(f"❌ Error processing webhook: {e}", exc_info=True)
        return Response(status_code=500, content="Internal server error")

@app.get("/")
async def root():
    """דף ברירת מחדל"""
    return {
        "status": "OK", 
        "service": "SLH Bot API", 
        "timestamp": time.time(),
        "version": "1.0.0",
        "message": "Bot is running!"
    }

@app.get("/health")
async def health_check():
    """Health check מקיף"""
    try:
        # בדיקת חיבור לבוט
        bot_info = await ptb_app.bot.get_me()
        
        # בדיקת webhook
        webhook_info = await ptb_app.bot.get_webhook_info()
        
        # בדיקת מסד נתונים
        db_ok = False
        try:
            db = SessionLocal()
            db.execute("SELECT 1")
            db_ok = True
            db.close()
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
        
        return {
            "status": "healthy",
            "bot_username": bot_info.username,
            "database": "connected" if db_ok else "disconnected",
            "webhook_url": webhook_info.url,
            "pending_updates": webhook_info.pending_update_count,
            "webhook_configured": webhook_info.url != "",
            "environment": settings.environment
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.post("/reset-webhook")
async def reset_webhook():
    """איפוס webhook - שימושי לניפוי בעיות"""
    try:
        logger.info("🔄 Resetting webhook...")
        
        await ptb_app.bot.delete_webhook(drop_pending_updates=True)
        time.sleep(3)
        
        if settings.webhook_url:
            hook_url = f"{settings.webhook_url}/{settings.bot_token}"
            await ptb_app.bot.set_webhook(
                url=hook_url,
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query", "inline_query"]
            )
        
        webhook_info = await ptb_app.bot.get_webhook_info()
        
        return {
            "success": True,
            "message": "Webhook reset successfully",
            "webhook_url": webhook_info.url,
            "pending_updates": webhook_info.pending_update_count,
            "has_custom_certificate": webhook_info.has_custom_certificate
        }
    except Exception as e:
        logger.error(f"Webhook reset failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/test-webhook")
async def test_webhook():
    """בדיקת webhook"""
    try:
        webhook_info = await ptb_app.bot.get_webhook_info()
        
        return {
            "webhook_url": webhook_info.url,
            "pending_updates": webhook_info.pending_update_count,
            "has_custom_certificate": webhook_info.has_custom_certificate,
            "last_error_date": webhook_info.last_error_date,
            "last_error_message": webhook_info.last_error_message,
            "max_connections": webhook_info.max_connections
        }
    except Exception as e:
        return {"error": str(e)}

# ========= STATIC FILES =========

# הגשה של קבצים סטטיים לאתר
if os.path.isdir("docs"):
    app.mount("/", StaticFiles(directory="docs", html=True), name="docs")
    logger.info("Mounted static files at /")

# ========= RUN SERVER =========

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="debug")
