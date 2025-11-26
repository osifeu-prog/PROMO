from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    Float,
    BigInteger,
)
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # חשוב: BigInteger – כדי לתמוך ב-Telegram IDs ארוכים (כמו 7757102350)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    password_hash = Column(String, nullable=True)  # שימוש עתידי לאדמין
    active_sessions = Column(Integer, default=0)

    # קשרים
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")


class Portfolio(Base):
    """
    פניות משקיעים / פורטפוליו – כשמשקיע כותב לבוט, אפשר לשמור את זה כאן.
    """
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    title = Column(String, nullable=True)        # כותרת כללית לפנייה / השקעה
    description = Column(String, nullable=True)  # תוכן חופשי שהמשקיע כתב
    links = Column(String, nullable=True)        # לינקים רלוונטיים (טקסט חופשי או JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="portfolios")


class Link(Base):
    """
    קישורים כלליים – אפשר להשתמש כדי לשמור לינקים חיצוניים,
    תיקים, אתרים וכו' (עתידי / להרחבה).
    """
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    url = Column(String, nullable=False)
    label = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Content(Base):
    """
    תוכן (לא “שיעורים”) – אפשר להציג למשקיעים / קהילה (עתידי).
    """
    __tablename__ = "contents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)
    category = Column(String, nullable=True)   # למשל: "investor", "academy", "update"
    created_at = Column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    """
    טרנזקציות – תשלומים / השקעות / רישום ל-39 ש"ח וכו'.
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    amount = Column(Float, nullable=False)              # סכום (בדולרים או בש"ח – אתה מחליט)
    status = Column(String, default="pending")          # pending / approved / rejected
    contract_hash = Column(String, nullable=True)       # hash של "חוזה" / רפרנס להצעה
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")
