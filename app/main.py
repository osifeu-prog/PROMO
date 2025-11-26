from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
from contextlib import asynccontextmanager
from datetime import datetime
import os

from app.core.config import settings
from app.core.database import engine
from app.models import database_models
from app.core.logging_config import logger

# נמחק זמנית את ה-imports של endpoints עד שנתקן אותם
try:
    from app.api.endpoints import auth, users, items
    from app.utils.logger import log_api_request
    HAS_ENDPOINTS = True
except ImportError as e:
    logger.warning(f"Some endpoints not available: {e}")
    HAS_ENDPOINTS = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    # בעת התחלה
    logger.info("🚀 Application starting up...")
    try:
        # ניסיון ליצור טבלאות - אם יש database
        database_models.Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.warning(f"⚠️ Could not create database tables: {e}")
    
    yield
    
    # בעת כיבוי
    logger.info("🛑 Application shutting down...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# Middleware בסיסי
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware ללוגים - רק אם יש את הפונקציה
if HAS_ENDPOINTS:
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        
        try:
            log_api_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(process_time, 2)
            )
        except Exception as e:
            logger.error(f"Logging error: {e}")
        
        return response

# Routes בסיסיות - ללא תלות ב-database
@app.get("/")
async def root():
    return {
        "message": "🚀 Welcome to My FastAPI App!",
        "version": settings.VERSION,
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check פשוט וללא תלות ב-database"""
    return {
        "status": "healthy", 
        "service": "fastapi",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "development")
    }

@app.get("/health/detailed")
async def detailed_health_check():
    """Health check מפורט יותר"""
    try:
        # בדיקה שהאפליקציה יכולה לגשת ל-database (לא חובה)
        from app.core.database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat(),
        "python_version": os.getenv("PYTHON_VERSION", "unknown")
    }

# ננסה להוסיף endpoints אם הם זמינים
if HAS_ENDPOINTS:
    try:
        app.include_router(auth.router, prefix="/api/v1", tags=["authentication"])
        app.include_router(users.router, prefix="/api/v1", tags=["users"])
        app.include_router(items.router, prefix="/api/v1", tags=["items"])
        logger.info("✅ All endpoints loaded successfully")
    except Exception as e:
        logger.error(f"❌ Failed to load some endpoints: {e}")

# Error handlers
@app.exception_handler(404)
async def not_found(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={"message": "Resource not found", "path": str(request.url)}
    )

@app.exception_handler(500)
async def server_error(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"}
    )

# Route פשוטה לבדיקת חיים נוספים
@app.get("/live")
async def liveness_check():
    return {"status": "alive"}
