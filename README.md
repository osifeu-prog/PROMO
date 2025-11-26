import os
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from telegram import Update
from telegram.ext import Application
from telegram.error import TelegramError
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database import engine, Base, get_db
from app.bot import setup_handlers
from app import crud
from app.schemas import StatsOut

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
        self.allowed_hosts = os.getenv("ALLOWED_HOSTS", "").split(",")
        
        if not self.bot_token:
            raise ValueError("BOT_TOKEN environment variable is required")

settings = Settings()

# ========= DB INIT =========

def init_db() -> bool:
    """
    אתחול מסד הנתונים עם טיפול בשגיאות
    מחזיר True אם הצליח, False אחרת
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting database initialization (attempt {attempt + 1}/{max_retries})")
            
            # רק בסביבת פיתוח - drop tables
            if settings.environment == "development":
                logger.info("Development environment - dropping tables")
                Base.metadata.drop_all(bind=engine)
            
            Base.metadata.create_all(bind=engine)
            logger.info("Database schema initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)  # המתנה לפני ניסיון חוזר
            else:
                logger.critical("All database initialization attempts failed")
                return False
    
    return False

# ניסיון אתחול DB - אבל לא נעצור את האפליקציה אם זה נכשל
db_init_success = init_db()
if not db_init_success and settings.environment == "production":
    logger.warning("Continuing with failed DB initialization - some features may not work")

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
    
    # אתחול Telegram Bot
    startup_success = False
    try:
        await ptb_app.initialize()
        logger.info("Telegram application initialized")

        # הגדרת webhook אם קיים URL
        if settings.webhook_url:
            hook_url = f"{settings.webhook_url}/{settings.bot_token}"
            try:
                webhook_info = await ptb_app.bot.get_webhook_info()
                if webhook_info.url != hook_url:
                    await ptb_app.bot.set_webhook(url=hook_url)
                    logger.info(f"Webhook set to {hook_url}")
                else:
                    logger.info("Webhook already set correctly")
            except TelegramError as e:
                logger.error(f"Failed to set webhook: {e}")
                if settings.environment == "production":
                    raise
        else:
            logger.warning("No WEBHOOK_URL set - using polling mode")

        await ptb_app.start()
        startup_success = True
        logger.info("Application startup completed successfully")

    except Exception as e:
        logger.critical(f"Application startup failed: {e}")
        if settings.environment == "production":
            raise

    try:
        yield
    finally:
        logger.info("Shutting down application...")
        try:
            if startup_success:
                if settings.webhook_url:
                    try:
                        await ptb_app.bot.delete_webhook(drop_pending_updates=True)
                        logger.info("Webhook deleted successfully")
                    except TelegramError as e:
                        logger.warning(f"Failed to delete webhook: {e}")
                
                await ptb_app.stop()
                await ptb_app.shutdown()
                logger.info("Telegram application stopped successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        logger.info("Application shutdown completed")

# ========= FASTAPI APP =========

app = FastAPI(
    title="SLH Investor Bot & Landing",
    description="Telegram bot and landing page for SLH investors",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

# ========= MIDDLEWARE =========

# CORS middleware
if settings.allowed_hosts and settings.allowed_hosts != [""]:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_hosts,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

# Trusted Host middleware
if settings.environment == "production" and settings.allowed_hosts:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code}",
        extra={
            "processing_time": round(process_time, 3),
            "status_code": response.status_code,
            "method": request.method,
            "path": request.url.path
        }
    )
    
    return response

# ========= STATIC FILES =========

# דף המשקיעים
if os.path.isdir("docs"):
    app.mount(
        "/investors",
        StaticFiles(directory="docs", html=True),
        name="investors",
    )
    logger.info("Mounted /investors static files")
else:
    logger.warning("docs directory not found - /investors endpoint will not work")

# נכסים סטטיים
if os.path.isdir("docs/images"):
    app.mount(
        "/assets",
        StaticFiles(directory="docs/images"),
        name="assets",
    )
    logger.info("Mounted /assets static files")
else:
    logger.warning("docs/images directory not found - /assets endpoint will not work")

# ========= ROUTES =========

@app.post(f"/{settings.bot_token}")
async def telegram_webhook(request: Request):
    """
    נקודת Webhook שמטפלת בכל העדכונים מטלגרם.
    """
    # Log basic info
    client_host = request.client.host if request.client else "unknown"
    logger.info(f"Webhook request from {client_host}")

    try:
        raw_body = await request.body()
        body_size = len(raw_body)
        logger.debug(f"Webhook payload size: {body_size} bytes")

        # Validation
        if body_size > 1024 * 1024:  # 1MB max
            logger.warning(f"Payload too large: {body_size} bytes")
            return Response(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

        if body_size == 0:
            logger.warning("Empty webhook payload")
            return Response(status_code=status.HTTP_400_BAD_REQUEST)

        # Parse JSON
        try:
            data = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook: {e}")
            return Response(
                status_code=status.HTTP_400_BAD_REQUEST,
                content="Invalid JSON format"
            )

        # Process Telegram update
        try:
            update = Update.de_json(data, ptb_app.bot)
            if update:
                await ptb_app.process_update(update)
                logger.debug(f"Processed update ID: {update.update_id}")
            else:
                logger.warning("Received null update from Telegram")
                
        except TelegramError as e:
            logger.error(f"Telegram API error: {e}")
            return Response(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content="Telegram API error"
            )
        except Exception as e:
            logger.error(f"Error processing update: {e}")
            return Response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content="Internal server error"
            )

        return Response(status_code=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Unexpected error in webhook: {e}")
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content="Internal server error"
        )


@app.get("/")
async def root():
    """הפניה אוטומטית לדף המשקיעים"""
    return Response(
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={"Location": "/investors"},
    )


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check מקיף עם בדיקת כל הרכיבים"""
    health_status: Dict[str, Any] = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "0.1.0",
        "environment": settings.environment
    }
    
    overall_status = "healthy"
    
    # בדיקת מסד נתונים
    try:
        db.execute("SELECT 1")
        health_status["database"] = "connected"
    except SQLAlchemyError as e:
        health_status["database"] = "disconnected"
        health_status["database_error"] = str(e)
        overall_status = "unhealthy"
        logger.error(f"Database health check failed: {e}")
    
    # בדיקת Telegram Bot
    try:
        bot_info = await ptb_app.bot.get_me()
        health_status["telegram_bot"] = "connected"
        health_status["bot_username"] = bot_info.username
    except TelegramError as e:
        health_status["telegram_bot"] = "disconnected"
        health_status["telegram_error"] = str(e)
        overall_status = "unhealthy"
        logger.error(f"Telegram bot health check failed: {e}")
    
    health_status["status"] = overall_status
    
    # אם לא בריא - מחזירים status code מתאים
    if overall_status == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status
        )
    
    return health_status


@app.get("/api/stats", response_model=StatsOut)
def api_stats(db: Session = Depends(get_db)):
    """מחזיר סטטיסטיקות של המערכת"""
    try:
        stats = crud.get_stats(db)
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Statistics not available"
            )
        return StatsOut(**stats)
    except SQLAlchemyError as e:
        logger.error(f"Database error in stats endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error in stats endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/favicon.ico")
async def favicon():
    """מניעת שגיאות עבור favicon"""
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ========= ERROR HANDLERS =========

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """טיפול בשגיאות 404"""
    logger.info(f"404 Not Found: {request.url}")
    return Response(
        status_code=status.HTTP_404_NOT_FOUND,
        content="Endpoint not found"
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    """טיפול בשגיאות 500"""
    logger.error(f"500 Internal Server Error for {request.url}: {exc}")
    return Response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content="Internal server error"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        log_level="info"
    )


























from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# קבלת DATABASE_URL מהסביבה, עם ערך ברירת מחדל ל-SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./slh_bot.db")

# יצירת ה-engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# יצירת SessionLocal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# בסיס עבור המודלים
Base = declarative_base()

# Dependency לקבלת session של DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

























from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserOut(UserBase):
    id: int
    is_admin: bool
    active_sessions: int
    created_at: datetime

    class Config:
        from_attributes = True

# Portfolio Schemas
class PortfolioBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    links: Optional[List[dict]] = None  # רשימה של קישורים

class PortfolioCreate(PortfolioBase):
    pass

class PortfolioOut(PortfolioBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Content Schemas
class ContentBase(BaseModel):
    title: str
    body: str
    category: Optional[str] = None
    order_index: int = 0
    is_published: bool = False

class ContentCreate(ContentBase):
    pass

class ContentOut(ContentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Transaction Schemas
class TransactionBase(BaseModel):
    amount: float
    currency: str = "USD"
    transaction_type: str
    description: Optional[str] = None
    contract_hash: Optional[str] = None
    payment_method: Optional[str] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionOut(TransactionBase):
    id: int
    user_id: int
    status: str
    timestamp: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Stats Schema
class StatsOut(BaseModel):
    total_users: int
    total_transactions: int
    total_portfolios: int
    total_revenue: float
    active_users: int





        









    
    
