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

from app.database import engine, Base, get_db
from app.bot import setup_handlers
from app import crud

# ========= LOGGING SETUP =========

logging.basicConfig(
    level=logging.INFO,
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

settings = Settings()

# ========= DB INIT =========

def init_db():
    """אתחול מסד הנתונים"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

init_db()

# ========= TELEGRAM APPLICATION =========

try:
    ptb_app = Application.builder().token(settings.bot_token).build()
    setup_handlers(ptb_app)
    logger.info("Telegram application initialized successfully")
except Exception as e:
    logger.critical(f"Failed to initialize Telegram application: {e}")
    raise

# ========= LIFESPAN =========

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting application in {settings.environment} mode")
    
    try:
        await ptb_app.initialize()
        logger.info("Telegram application initialized")

        # הגדרת webhook
        if settings.webhook_url:
            hook_url = f"{settings.webhook_url}/{settings.bot_token}"
            try:
                # מחיקת webhook קיים והגדרה מחדש
                await ptb_app.bot.delete_webhook(drop_pending_updates=True)
                time.sleep(1)
                await ptb_app.bot.set_webhook(
                    url=hook_url,
                    drop_pending_updates=True,
                    allowed_updates=["message", "callback_query"]
                )
                logger.info(f"Webhook set to: {hook_url}")
                
                # בדיקת webhook
                webhook_info = await ptb_app.bot.get_webhook_info()
                logger.info(f"Webhook info: URL={webhook_info.url}, Pending={webhook_info.pending_update_count}")
                
            except TelegramError as e:
                logger.error(f"Failed to set webhook: {e}")
        else:
            logger.warning("No WEBHOOK_URL set")

        await ptb_app.start()
        logger.info("Application startup completed successfully")

    except Exception as e:
        logger.critical(f"Application startup failed: {e}")

    try:
        yield
    finally:
        logger.info("Shutting down application...")
        try:
            await ptb_app.stop()
            await ptb_app.shutdown()
            logger.info("Telegram application stopped successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# ========= FASTAPI APP =========

app = FastAPI(
    title="SLH Ecosystem API",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
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
        data = json.loads(body.decode('utf-8'))
        
        # לוג בסיסי
        update_id = data.get('update_id', 'unknown')
        logger.info(f"Received update {update_id}")
        
        # עיבוד העדכון
        update = Update.de_json(data, ptb_app.bot)
        await ptb_app.process_update(update)
        
        return Response(status_code=200)
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return Response(status_code=400, content="Invalid JSON")
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return Response(status_code=500, content="Internal server error")

@app.get("/")
async def root():
    """דף ברירת מחדל"""
    return {"status": "OK", "service": "SLH Bot", "timestamp": time.time()}

@app.get("/health")
async def health_check():
    """Health check"""
    try:
        bot_info = await ptb_app.bot.get_me()
        return {
            "status": "healthy",
            "bot_username": bot_info.username,
            "webhook_set": True
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.post("/reset-webhook")
async def reset_webhook():
    """איפוס webhook"""
    try:
        await ptb_app.bot.delete_webhook(drop_pending_updates=True)
        time.sleep(2)
        
        hook_url = f"{settings.webhook_url}/{settings.bot_token}"
        await ptb_app.bot.set_webhook(
            url=hook_url,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
        
        webhook_info = await ptb_app.bot.get_webhook_info()
        
        return {
            "success": True,
            "webhook_url": webhook_info.url,
            "pending_updates": webhook_info.pending_update_count
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# ========= STATIC FILES =========

if os.path.isdir("docs"):
    app.mount("/investors", StaticFiles(directory="docs", html=True), name="investors")
    logger.info("Mounted /investors static files")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
