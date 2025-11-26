from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from typing import List, Optional, Dict, Any
import logging
from passlib.context import CryptContext

from app.models import User, Portfolio, Link, Content, Transaction
from app.schemas import UserCreate, PortfolioCreate, TransactionCreate, ContentCreate

logger = logging.getLogger(__name__)

# ניהול סיסמאות
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ========= USER CRUD =========
def get_user_by_telegram_id(db: Session, telegram_id: int) -> Optional[User]:
    """מחזיר משתמש לפי telegram_id"""
    try:
        return db.query(User).filter(User.telegram_id == telegram_id).first()
    except SQLAlchemyError as e:
        logger.error(f"Error getting user by telegram_id {telegram_id}: {e}")
        return None

def create_user(db: Session, user_data: UserCreate) -> Optional[User]:
    """יוצר משתמש חדש"""
    try:
        # בדיקה אם המשתמש כבר קיים
        existing_user = get_user_by_telegram_id(db, user_data.telegram_id)
        if existing_user:
            logger.info(f"User {user_data.telegram_id} already exists")
            return existing_user
        
        db_user = User(
            telegram_id=user_data.telegram_id,
            username=user_data.username,
            first_name=getattr(user_data, 'first_name', None),
            last_name=getattr(user_data, 'last_name', None)
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"Created new user: {db_user.telegram_id}")
        return db_user
    except IntegrityError:
        db.rollback()
        logger.info(f"User {user_data.telegram_id} already exists")
        return get_user_by_telegram_id(db, user_data.telegram_id)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating user: {e}")
        return None

def update_user(db: Session, telegram_id: int, update_data: Dict[str, Any]) -> Optional[User]:
    """מעדכן משתמש קיים"""
    try:
        user = get_user_by_telegram_id(db, telegram_id)
        if not user:
            logger.warning(f"User {telegram_id} not found for update")
            return None
        
        for key, value in update_data.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        db.commit()
        db.refresh(user)
        logger.info(f"Updated user: {telegram_id}")
        return user
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user {telegram_id}: {e}")
        return None

def make_admin(db: Session, telegram_id: int, password: str) -> Optional[User]:
    """הופך משתמש למנהל"""
    try:
        user = get_user_by_telegram_id(db, telegram_id)
        if not user:
            logger.warning(f"User {telegram_id} not found for admin promotion")
            return None
        
        user.is_admin = True
        user.hashed_password = hash_password(password)
        
        db.commit()
        db.refresh(user)
        logger.info(f"Promoted user {telegram_id} to admin")
        return user
    except Exception as e:
        db.rollback()
        logger.error(f"Error making user {telegram_id} admin: {e}")
        return None

# ========= TRANSACTION CRUD =========
def create_transaction(db: Session, user_id: int, amount: float, 
                      transaction_type: str = "payment", 
                      details: Optional[Dict] = None) -> Optional[Transaction]:
    """יוצר טרנזקציה חדשה"""
    try:
        db_transaction = Transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type,
            description=details.get('description') if details else None,
            currency=details.get('currency', 'USD') if details else 'USD'
        )
        
        db.add(db_transaction)
        db.commit()
        db.refresh(db_transaction)
        logger.info(f"Created transaction for user {user_id}: {amount}")
        return db_transaction
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating transaction for user {user_id}: {e}")
        return None

def get_user_transactions(db: Session, user_id: int, limit: int = 50) -> List[Transaction]:
    """מחזיר את הטרנזקציות של משתמש"""
    try:
        return (db.query(Transaction)
                .filter(Transaction.user_id == user_id)
                .order_by(Transaction.timestamp.desc())
                .limit(limit)
                .all())
    except SQLAlchemyError as e:
        logger.error(f"Error getting transactions for user {user_id}: {e}")
        return []

# ========= STATISTICS =========
def get_stats(db: Session) -> Dict[str, Any]:
    """מחזיר סטטיסטיקות כלליות"""
    try:
        total_users = db.query(User).count()
        total_transactions = db.query(Transaction).count()
        
        revenue_result = db.query(db.func.sum(Transaction.amount)).filter(
            Transaction.status == 'completed'
        ).scalar()
        total_revenue = float(revenue_result) if revenue_result else 0.0
        
        return {
            "total_users": total_users,
            "total_transactions": total_transactions,
            "total_revenue": total_revenue,
            "active_users": db.query(User).filter(User.active_sessions > 0).count(),
        }
    except SQLAlchemyError as e:
        logger.error(f"Error getting stats: {e}")
        return {}
