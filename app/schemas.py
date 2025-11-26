from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserOut(UserBase):
    id: int
    is_admin: bool
    active_sessions: int
    created_at: datetime

    class Config:
        from_attributes = True

# Portfolio Schemas
class PortfolioBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    links: Optional[List[dict]] = None  # רשימה של קישורים

class PortfolioCreate(PortfolioBase):
    pass

class PortfolioOut(PortfolioBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Content Schemas
class ContentBase(BaseModel):
    title: str
    body: str
    category: Optional[str] = None
    order_index: int = 0
    is_published: bool = False

class ContentCreate(ContentBase):
    pass

class ContentOut(ContentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Transaction Schemas
class TransactionBase(BaseModel):
    amount: float
    currency: str = "USD"
    transaction_type: str
    description: Optional[str] = None
    contract_hash: Optional[str] = None
    payment_method: Optional[str] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionOut(TransactionBase):
    id: int
    user_id: int
    status: str
    timestamp: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Stats Schema
class StatsOut(BaseModel):
    total_users: int
    total_transactions: int
    total_portfolios: int
    total_revenue: float
    active_users: int
