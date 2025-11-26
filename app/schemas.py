from pydantic import BaseModel

class UserCreate(BaseModel):
    telegram_id: int
    username: str

class PortfolioCreate(BaseModel):
    title: str
    description: str
    links: str

# Add more as needed for links, contents, transactions
