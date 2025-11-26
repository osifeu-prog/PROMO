from sqlalchemy import func
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
    """Promote a user to admin with a password hash (for future use)."""
    db_user = get_user_by_telegram_id(db, telegram_id)
    if not db_user:
        db_user = User(telegram_id=telegram_id, username=None)
        db.add(db_user)
    db_user.is_admin = True
    db_user.password_hash = hash_password(password)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_portfolio(db: Session, user_id: int, portfolio: PortfolioCreate):
    db_portfolio = Portfolio(
        user_id=user_id,
        title=portfolio.title,
        description=portfolio.description,
        links=portfolio.links,
    )
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio


def create_transaction(db: Session, user_id: int, amount: float, details: str):
    contract_hash = generate_contract_hash(details)
    db_transaction = Transaction(
        user_id=user_id,
        amount=amount,
        contract_hash=contract_hash,
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction


def get_stats(db: Session):
    """Return basic aggregate stats for admin / investors dashboards."""
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_transactions = db.query(func.count(Transaction.id)).scalar() or 0
    total_amount = db.query(func.coalesce(func.sum(Transaction.amount), 0)).scalar() or 0.0

    return {
        "total_users": int(total_users),
        "total_transactions": int(total_transactions),
        "total_amount_usd": float(total_amount),
    }

# Future extensions:
# - get_links
# - update_content
# - advanced stats per cohort / funnel
