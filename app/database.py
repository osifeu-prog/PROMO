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
