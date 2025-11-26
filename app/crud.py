from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, schemas
from app.utils import generate_contract_hash


def get_user_by_telegram_id(db: Session, telegram_id: int):
    return db.query(models.User).filter(models.User.telegram_id == telegram_id).first()


def create_user(db: Session, user: schemas.UserCreate, is_admin: bool = False):
    db_user = models.User(
        telegram_id=user.telegram_id,
        username=user.username,
        is_admin=is_admin,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def make_admin(db: Session, user: models.User):
    user.is_admin = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_portfolio(db: Session, user_id: int, portfolio: schemas.PortfolioCreate):
    db_portfolio = models.Portfolio(
        user_id=user_id,
        title=portfolio.title,
        description=portfolio.description,
        links=portfolio.links,
    )
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio


def create_transaction(db: Session, user_id: int, tx: schemas.TransactionCreate):
    contract_hash = generate_contract_hash(tx.details)
    db_tx = models.Transaction(
        user_id=user_id,
        amount=tx.amount,
        currency=tx.currency,
        details=tx.details,
        contract_hash=contract_hash,
    )
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx


def get_stats(db: Session) -> schemas.StatsOut:
    total_users = db.query(func.count(models.User.id)).scalar() or 0
    total_transactions = db.query(func.count(models.Transaction.id)).scalar() or 0
    total_amount = db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0)).scalar() or 0.0
    return schemas.StatsOut(
        total_users=total_users,
        total_transactions=total_transactions,
        total_amount_usd=float(total_amount),
    )
