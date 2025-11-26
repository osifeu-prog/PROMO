from typing import Optional
from pydantic import BaseModel

class UserCreate(BaseModel):
    telegram_id: int
    username: str

class PortfolioCreate(BaseModel):
    title: str
    description: str
    links: Optional[str] = None

class StatsOut(BaseModel):
    total_users: int
    total_transactions: int
    total_amount_usd: float
