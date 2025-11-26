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
    # שימוש ב-BigInteger כדי לתמוך ב-Telegram IDs כמו 7757102350
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    password_hash = Column(String, nullable=True)
    active_sessions = Column(Integer, default=0)

    portfolios = relationship(
        "Portfolio",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    transactions = relationship(
        "Transaction",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Portfolio(Base):
    """
    פניות משקיעים / פורטפוליו – כל הודעה מהמשקיע יכולה להישמר כאן.
    """
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    title = Column(String, nullable=True)
    description = Column(String, nullable=True)
    links = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="portfolios")


class Link(Base):
    """
    קישורים כלליים – לשימוש עתידי (תיקי השקעות, אתרים וכו').
    """
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    url = Column(String, nullable=False)
    label = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Content(Base):
    """
    תוכן (במקום 'שיעורים') – להצגה באתר/בוט.
    """
    __tablename__ = "contents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)
    category = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    """
    טרנזקציות – תשלומים / השקעות / 39 ש"ח וכו'.
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    amount = Column(Float, nullable=False)
    status = Column(String, default="pending")
    contract_hash = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")
