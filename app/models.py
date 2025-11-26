from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, 
    DateTime, Float, BigInteger, Text, JSON, func, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
import enum

from app.database import Base

# Enums להגדרות ברורות
class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class TransactionType(str, enum.Enum):
    INVESTMENT = "investment"
    PAYMENT = "payment"
    FEE = "fee"
    SUBSCRIPTION = "subscription"

class ContentCategory(str, enum.Enum):
    EDUCATIONAL = "educational"
    NEWS = "news"
    UPDATE = "update"
    TUTORIAL = "tutorial"
    GENERAL = "general"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    is_admin = Column(Boolean, default=False)
    hashed_password = Column(String(255), nullable=True)
    active_sessions = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    last_seen = Column(DateTime, nullable=True)

    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    links = relationship("Link", back_populates="user", cascade="all, delete-orphan")

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    links = Column(JSON, nullable=True)
    status = Column(String(50), default="draft")
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="portfolios")

class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    url = Column(String(500), nullable=False)
    label = Column(String(100), nullable=True)
    link_type = Column(String(50), default="general")
    
    created_at = Column(DateTime, server_default=func.now())
    
    user = relationship("User", back_populates="links")

class Content(Base):
    __tablename__ = "contents"

    id = Column(Integer, primary_key=True, index=True)
    
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    order_index = Column(Integer, default=0)
    is_published = Column(Boolean, default=False)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    published_at = Column(DateTime, nullable=True)

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    
    description = Column(String(500), nullable=True)
    contract_hash = Column(String(255), nullable=True)
    payment_method = Column(String(50), nullable=True)
    
    timestamp = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="transactions")
