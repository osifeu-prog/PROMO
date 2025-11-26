from sqlalchemy.orm import Session
from app.models import User, Portfolio, Link, Content, Transaction
from app.utils import hash_password, generate_contract_hash
from app.schemas import UserCreate, PortfolioCreate

def get_user_by_telegram_id(db: Session, telegram_id: int):
    return db.query(User).filter(User.telegram_id == telegram_id).first()

def create_user(db: Session, user: UserCreate):
    db_user = User(telegram_id=user.telegram_id, username=user.username)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def make_admin(db: Session, telegram_id: int, password: str):
    user = get_user_by_telegram_id(db, telegram_id)
    if user:
        user.is_admin = True
        user.password_hash = hash_password(password)
        db.commit()
        return user

# Similar for portfolio, link, content, transaction
def create_portfolio(db: Session, portfolio: PortfolioCreate, user_id: int):
    db_portfolio = Portfolio(**portfolio.dict(), user_id=user_id)
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

def create_transaction(db: Session, user_id: int, amount: float, details: str):
    contract_hash = generate_contract_hash(details)
    db_transaction = Transaction(user_id=user_id, amount=amount, contract_hash=contract_hash)
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

# Add get_links, update_content, etc.
