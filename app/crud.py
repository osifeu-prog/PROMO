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

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """מחזיר משתמש לפי ID"""
    try:
        return db.query(User).filter(User.id == user_id).first()
    except SQLAlchemyError as e:
        logger.error(f"Error getting user by id {user_id}: {e}")
        return None

def create_user(db: Session, user_data: UserCreate) -> Optional[User]:
    """יוצר משתמש חדש עם טיפול בשגיאות"""
    try:
        # בדיקה אם המשתמש כבר קיים
        existing_user = get_user_by_telegram_id(db, user_data.telegram_id)
        if existing_user:
            logger.warning(f"User with telegram_id {user_data.telegram_id} already exists")
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
        logger.warning(f"User with telegram_id {user_data.telegram_id} already exists (IntegrityError)")
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

def verify_admin_password(db: Session, telegram_id: int, password: str) -> bool:
    """בודק סיסמת מנהל"""
    user = get_user_by_telegram_id(db, telegram_id)
    if not user or not user.is_admin or not user.hashed_password:
        return False
    
    return verify_password(password, user.hashed_password)

def get_users_count(db: Session) -> int:
    """מחזיר את מספר המשתמשים הכולל"""
    try:
        return db.query(User).count()
    except SQLAlchemyError as e:
        logger.error(f"Error getting users count: {e}")
        return 0

# ========= PORTFOLIO CRUD =========
def create_portfolio(db: Session, portfolio_data: PortfolioCreate, user_id: int) -> Optional[Portfolio]:
    """יוצר פורטפוליו חדש"""
    try:
        db_portfolio = Portfolio(
            **portfolio_data.model_dump(),
            user_id=user_id
        )
        
        db.add(db_portfolio)
        db.commit()
        db.refresh(db_portfolio)
        logger.info(f"Created portfolio for user {user_id}")
        return db_portfolio
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating portfolio for user {user_id}: {e}")
        return None

def get_user_portfolios(db: Session, user_id: int) -> List[Portfolio]:
    """מחזיר את כל הפורטפוליו של משתמש"""
    try:
        return db.query(Portfolio).filter(Portfolio.user_id == user_id).order_by(Portfolio.created_at.desc()).all()
    except SQLAlchemyError as e:
        logger.error(f"Error getting portfolios for user {user_id}: {e}")
        return []

# ========= TRANSACTION CRUD =========
def create_transaction(db: Session, user_id: int, amount: float, 
                      transaction_type: str = "payment", 
                      details: Optional[Dict] = None) -> Optional[Transaction]:
    """יוצר טרנזקציה חדשה"""
    try:
        from app.utils import generate_contract_hash
        
        contract_hash = generate_contract_hash(str(details) if details else "")
        
        db_transaction = Transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type,
            contract_hash=contract_hash,
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

# ========= CONTENT CRUD =========
def create_content(db: Session, content_data: ContentCreate) -> Optional[Content]:
    """יוצר תוכן חדש"""
    try:
        db_content = Content(**content_data.model_dump())
        db.add(db_content)
        db.commit()
        db.refresh(db_content)
        logger.info(f"Created content: {content_data.title}")
        return db_content
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating content: {e}")
        return None

def get_published_content(db: Session, category: Optional[str] = None) -> List[Content]:
    """מחזיר תוכן שפורסם"""
    try:
        query = db.query(Content).filter(Content.is_published == True)
        if category:
            query = query.filter(Content.category == category)
        return query.order_by(Content.order_index, Content.created_at.desc()).all()
    except SQLAlchemyError as e:
        logger.error(f"Error getting published content: {e}")
        return []

# ========= STATISTICS =========
def get_stats(db: Session) -> Dict[str, Any]:
    """מחזיר סטטיסטיקות כלליות"""
    try:
        total_users = db.query(User).count()
        total_transactions = db.query(Transaction).count()
        total_portfolios = db.query(Portfolio).count()
        total_revenue = db.query(db.func.sum(Transaction.amount)).filter(
            Transaction.status == 'completed'
        ).scalar() or 0
        
        pending_transactions = db.query(Transaction).filter(
            Transaction.status == 'pending'
        ).count()
        
        completed_transactions = db.query(Transaction).filter(
            Transaction.status == 'completed'
        ).count()
        
        avg_transaction = db.query(db.func.avg(Transaction.amount)).filter(
            Transaction.status == 'completed'
        ).scalar() or 0
        
        return {
            "total_users": total_users,
            "total_transactions": total_transactions,
            "total_portfolios": total_portfolios,
            "total_revenue": float(total_revenue),
            "active_users": db.query(User).filter(User.active_sessions > 0).count(),
            "pending_transactions": pending_transactions,
            "completed_transactions": completed_transactions,
            "average_transaction": float(avg_transaction)
        }
    except SQLAlchemyError as e:
        logger.error(f"Error getting stats: {e}")
        return {}
