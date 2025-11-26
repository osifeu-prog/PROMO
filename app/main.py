from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
from contextlib import asynccontextmanager
from datetime import datetime
import os
import logging

from app.core.config import settings
from app.utils.logger import logger


# Setup basic logging
logging.basicConfig(level=logging.INFO)
# Use shared logger from app.utils.logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Application starting up on Railway...")
    logger.info(f"📊 Environment: {settings.RAILWAY_ENVIRONMENT}")
    logger.info(
        f"🔑 Bot Token: {'***' + settings.BOT_TOKEN[-4:] if settings.BOT_TOKEN else 'Not set'}"
    )

    # Initialize Telegram Bot if token exists
    if settings.BOT_TOKEN:
        try:
            from app.bot import initialize_bot

            await initialize_bot()
            logger.info("✅ Telegram bot initialized")
        except Exception as e:
            logger.error(f"❌ Telegram bot initialization failed: {e}")

    yield

    # Shutdown
    logger.info("🛑 Application shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url=settings.DOCS_URL,
    redoc_url=None if settings.DOCS_URL == "/docs" else "/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({process_time:.2f}ms)"
    )
    return response


# Basic Routes
@app.get("/")
async def root():
    return {
        "message": "🚀 Welcome to My FastAPI App on Railway!",
        "version": settings.VERSION,
        "environment": settings.RAILWAY_ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat(),
        "docs": settings.DOCS_URL,
    }


@app.get("/health")
async def health_check():
    """Health check for Railway"""
    health_data = {
        "status": "healthy",
        "service": "fastapi",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.RAILWAY_ENVIRONMENT,
        "version": settings.VERSION,
    }

    # Add bot status if available
    if settings.BOT_TOKEN:
        health_data["bot"] = "configured"

    # Add database status if available
    if settings.DATABASE_URL:
        try:
            from app.database import SessionLocal

            db = SessionLocal()
            db.execute("SELECT 1")
            db.close()
            health_data["database"] = "connected"
        except Exception as e:
            health_data["database"] = f"error: {str(e)}"

    return health_data


@app.get("/info")
async def app_info():
    """App information endpoint"""
    return {
        "app_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.RAILWAY_ENVIRONMENT,
        "commit_sha": settings.RAILWAY_GIT_COMMIT_SHA,
        "bot_configured": bool(settings.BOT_TOKEN),
        "admin_user_id": settings.ADMIN_USER_ID,
        "docs_url": settings.DOCS_URL,
    }


# Telegram Webhook Routes (if bot is configured)
if settings.BOT_TOKEN and settings.WEBHOOK_URL:

    @app.post("/webhook/telegram")
    async def telegram_webhook(update: dict):
        try:
            from app.bot import process_webhook

            await process_webhook(update)
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            raise HTTPException(status_code=500, detail="Webhook processing failed")


# Include API routes if they exist
try:
    from app.api.endpoints import auth, users, items

    app.include_router(
        auth.router, prefix=settings.API_V1_STR, tags=["authentication"]
    )
    app.include_router(users.router, prefix=settings.API_V1_STR, tags=["users"])
    app.include_router(items.router, prefix=settings.API_V1_STR, tags=["items"])
    logger.info("✅ API routes loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Some API routes not available: {e}")


# Error handlers
@app.exception_handler(404)
async def not_found(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={"message": "Resource not found", "path": str(request.url.path)},
    )


@app.exception_handler(500)
async def server_error(request: Request, exc: HTTPException):
    logger.error(f"Server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"},
    )


# Liveness probe for Railway (legacy)
@app.get("/live")
async def liveness_probe():
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}
