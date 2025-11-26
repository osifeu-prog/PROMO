import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging

logger = logging.getLogger("app.database")

# קבלת DATABASE_URL מהסביבה
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./slh_bot.db")

logger.info(f"🔧 Initializing database: {DATABASE_URL}")

# הגדרת engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    # עבור PostgreSQL
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency injection עבור sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """יצירת הטבלות במסד הנתונים"""
    try:
        # יבוא המודלים כאן כדי ש-SQLAlchemy יזהה אותם
        from app.models import User, Transaction, Portfolio, Content, Link
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {e}")
        return False
