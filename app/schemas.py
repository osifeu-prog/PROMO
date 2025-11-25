from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    telegram_id: int
    username: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserOut(UserBase):
    id: int
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True

class PortfolioCreate(BaseModel):
    title: str
    description: Optional[str] = None
    links: Optional[str] = None

class PortfolioOut(PortfolioCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class TransactionCreate(BaseModel):
    amount: float
    currency: str = "USD"
    details: str

class TransactionOut(TransactionCreate):
    id: int
    contract_hash: str
    created_at: datetime

    class Config:
        from_attributes = True

class LinkOut(BaseModel):
    id: int
    category: str
    label: str
    url: str

    class Config:
        from_attributes = True

class StatsOut(BaseModel):
    total_users: int
    total_transactions: int
    total_amount_usd: float
