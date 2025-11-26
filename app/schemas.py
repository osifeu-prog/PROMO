from pydantic import BaseModel, ConfigDict, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum

class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class TransactionType(str, Enum):
    INVESTMENT = "investment"
    PAYMENT = "payment"
    FEE = "fee"
    SUBSCRIPTION = "subscription"

class ContentCategory(str, Enum):
    EDUCATIONAL = "educational"
    NEWS = "news"
    UPDATE = "update"
    TUTORIAL = "tutorial"
    GENERAL = "general"

# ========= USER SCHEMAS =========

class UserBase(BaseModel):
    telegram_id: int = Field(..., description="Telegram user ID")
    username: Optional[str] = Field(None, description="Telegram username")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    active_sessions: Optional[int] = None

class UserOut(UserBase):
    id: int
    is_admin: bool
    active_sessions: int
    created_at: datetime
    last_seen: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class AdminCreate(BaseModel):
    telegram_id: int
    password: str = Field(..., min_length=6, description="Admin password")

class AdminLogin(BaseModel):
    telegram_id: int
    password: str

# ========= PORTFOLIO SCHEMAS =========

class PortfolioLink(BaseModel):
    url: str = Field(..., description="Link URL")
    label: Optional[str] = Field(None, description="Link display label")

class PortfolioBase(BaseModel):
    title: Optional[str] = Field(None, description="Portfolio title")
    description: Optional[str] = Field(None, description="Portfolio description")
    links: Optional[List[PortfolioLink]] = Field(None, description="List of links")

class PortfolioCreate(PortfolioBase):
    pass

class PortfolioUpdate(PortfolioBase):
    title: Optional[str] = None
    description: Optional[str] = None
    links: Optional[List[PortfolioLink]] = None
    status: Optional[str] = None

class PortfolioOut(PortfolioBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# ========= CONTENT SCHEMAS =========

class ContentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Content title")
    body: str = Field(..., min_length=1, description="Content body")
    category: Optional[ContentCategory] = Field(ContentCategory.GENERAL, description="Content category")
    order_index: int = Field(0, ge=0, description="Display order")

class ContentCreate(ContentBase):
    is_published: bool = Field(False, description="Publish status")

class ContentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    body: Optional[str] = Field(None, min_length=1)
    category: Optional[ContentCategory] = None
    order_index: Optional[int] = Field(None, ge=0)
    is_published: Optional[bool] = None

class ContentOut(ContentBase):
    id: int
    is_published: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# ========= TRANSACTION SCHEMAS =========

class TransactionBase(BaseModel):
    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: str = Field("USD", description="Currency code")
    transaction_type: TransactionType = Field(..., description="Type of transaction")
    description: Optional[str] = Field(None, description="Transaction description")
    payment_method: Optional[str] = Field(None, description="Payment method")

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return round(v, 2)

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    status: Optional[TransactionStatus] = None
    description: Optional[str] = None
    contract_hash: Optional[str] = None

class TransactionOut(TransactionBase):
    id: int
    user_id: int
    status: TransactionStatus
    contract_hash: Optional[str] = None
    timestamp: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# ========= LINK SCHEMAS =========

class LinkBase(BaseModel):
    url: str = Field(..., description="Link URL")
    label: Optional[str] = Field(None, description="Link label")
    link_type: Optional[str] = Field("general", description="Type of link")

class LinkCreate(LinkBase):
    pass

class LinkOut(LinkBase):
    id: int
    user_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ========= STATISTICS SCHEMAS =========

class StatsOut(BaseModel):
    total_users: int = Field(..., description="Total number of users")
    total_transactions: int = Field(..., description="Total number of transactions")
    total_portfolios: int = Field(..., description="Total number of portfolios")
    total_revenue: float = Field(..., description="Total revenue")
    active_users: int = Field(..., description="Number of active users")
    
    # שדות נוספים לסטטיסטיקות מתקדמות
    pending_transactions: Optional[int] = Field(0, description="Pending transactions")
    completed_transactions: Optional[int] = Field(0, description="Completed transactions")
    average_transaction: Optional[float] = Field(0, description="Average transaction amount")

    model_config = ConfigDict(from_attributes=True)

# ========= HEALTH CHECK SCHEMAS =========

class HealthCheck(BaseModel):
    status: str
    timestamp: float
    version: str
    environment: str
    database: str
    telegram_bot: str
    bot_username: Optional[str] = None

# ========= API RESPONSE SCHEMAS =========

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None

# ========= TELEGRAM WEBHOOK SCHEMAS =========

class TelegramWebhook(BaseModel):
    update_id: int
    message: Optional[Dict[str, Any]] = None
    edited_message: Optional[Dict[str, Any]] = None
    channel_post: Optional[Dict[str, Any]] = None
    edited_channel_post: Optional[Dict[str, Any]] = None
    inline_query: Optional[Dict[str, Any]] = None
    chosen_inline_result: Optional[Dict[str, Any]] = None
    callback_query: Optional[Dict[str, Any]] = None
    shipping_query: Optional[Dict[str, Any]] = None
    pre_checkout_query: Optional[Dict[str, Any]] = None
    poll: Optional[Dict[str, Any]] = None
    poll_answer: Optional[Dict[str, Any]] = None
    my_chat_member: Optional[Dict[str, Any]] = None
    chat_member: Optional[Dict[str, Any]] = None
    chat_join_request: Optional[Dict[str, Any]] = None
