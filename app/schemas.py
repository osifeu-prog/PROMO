from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
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

class TransactionBase(BaseModel):
    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: str = Field("USD", description="Currency code")
    transaction_type: TransactionType = Field(..., description="Type of transaction")
    description: Optional[str] = Field(None, description="Transaction description")
    payment_method: Optional[str] = Field(None, description="Payment method")

class TransactionCreate(TransactionBase):
    pass

class TransactionOut(TransactionBase):
    id: int
    user_id: int
    status: TransactionStatus
    contract_hash: Optional[str] = None
    timestamp: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None
