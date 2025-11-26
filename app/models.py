from datetime import datetime
import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    Float,
    BigInteger,
    Text,
    JSON,
    func,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship

from app.database import Base


# ===== Enums for clarity & data integrity =====

class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class TransactionType(str, enum.Enum):
    INVESTMENT = "investment"
    PAYMENT = "payment"
    FEE = "fee"


# ===== Core Models =====

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Telegram
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    # Admin / auth
    # שדה זה נשאר בשם password_hash כדי לא לשבור את crud/bot הקיימים
    # גם אם בפועל נשתמש בו להאש מוצפן בעתיד.
    is_admin = Column(Boolean, default=False)
    password_hash = Column(String(255), nullable=True)

    # Usage / sessions
    active_sessions = Column(Integer, default=0)

    # Auditing
    created_at = Column(DateTime, server_default=func.now())
    last_seen = Column(DateTime, nullable=True)

    # Relations
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
    links = relationship(
        "Link",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Portfolio(Base):
    """
    תיק השקעה / פנייה של משקיע – מה הוא מחפש, קישורים, סטטוס וכו'.
    """
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    title = Column(String(200), nullable=True)
    # תיאור ארוך – חופשי
    description = Column(Text, nullable=True)

    # רשימת קישורים כ-JSON:
    # [{ "url": "...", "label": "Deck" }, { "url": "...", "label": "Website" }]
    links = Column(JSON, nullable=True)

    # draft / published / archived וכו'
    status = Column(String(50), default="draft")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="portfolios")


class Link(Base):
    """
    קישורים כלליים של משתמש (social, אתר חברה, לינקדאין וכו').
    זה נפרד מה-links של Portfolio כדי שתוכל לשמור פרופיל משקיע כללי.
    """
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    url = Column(String(500), nullable=False)
    label = Column(String(100), nullable=True)
    # general / portfolio / social / deck / fund וכו'
    link_type = Column(String(50), default="general")

    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="links")


class Content(Base):
    """
    תוכן (במקום 'שיעורים') – דפי הסבר, FAQ, מצגות, מאמרים למשקיעים.
    """
    __tablename__ = "contents"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)  # investor, academy, update, etc.

    order_index = Column(Integer, default=0)
    is_published = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    published_at = Column(DateTime, nullable=True)


class Transaction(Base):
    """
    טרנזקציות – כל מה שקשור לתשלומים / השקעות / דמי גישה (39 ₪) וכו'.
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="ILS")  # ILS / USD / USDT וכו'

    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)

    description = Column(String(500), nullable=True)
    contract_hash = Column(String(255), nullable=True)
    payment_method = Column(String(50), nullable=True)  # bank_transfer / ton / card / crypto

    timestamp = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="transactions")
