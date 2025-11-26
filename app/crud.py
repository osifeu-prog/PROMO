import logging
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func

from app import models

logger = logging.getLogger("app.crud")


# ===== Users =====

def get_user_by_telegram_id(db: Session, telegram_id: int) -> Optional[models.User]:
    """
    מחזיר משתמש לפי telegram_id, או None אם לא קיים.
    """
    return (
        db.query(models.User)
        .filter(models.User.telegram_id == telegram_id)
        .first()
    )


def create_user(
    db: Session,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    is_admin: bool = False,
) -> models.User:
    """
    יוצר משתמש חדש.
    אם יש בעיית DB (כמו integer out of range / סכימה בעייתית),
    לא מפיל את הבוט – מחזיר אובייקט User זמני לשימוש לוגיקה של הבוט.
    """
    user = models.User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        is_admin=is_admin,
    )
    db.add(user)

    try:
        db.commit()
        db.refresh(user)
        logger.info("User %s (%s) created in DB", telegram_id, username)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(
            "DB error in create_user for telegram_id=%s – continuing without persisting user",
            telegram_id,
            exc_info=e,
        )
        # בשלב זה user הוא אובייקט בזיכרון בלבד (id כנראה None),
        # אבל הבוט יכול להמשיך להשתמש בו כדי לענות למשתמש.
    return user


# ===== Stats API =====

def get_stats(db: Session) -> Dict[str, Any]:
    """
    מחזיר סטטיסטיקות בסיסיות לבוט / API.
    גם כאן – אם יש שגיאה, לא מפיל את השרת.
    """
    stats: Dict[str, Any] = {
        "total_users": 0,
        "total_transactions": 0,
        "total_investment": 0.0,
    }

    try:
        stats["total_users"] = db.query(models.User).count()
    except SQLAlchemyError as e:
        logger.error("Failed to count users", exc_info=e)

    try:
        stats["total_transactions"] = db.query(models.Transaction).count()
    except SQLAlchemyError as e:
        logger.error("Failed to count transactions", exc_info=e)

    try:
        total_investment = (
            db.query(
                func.coalesce(func.sum(models.Transaction.amount), 0.0)
            )
            .filter(
                models.Transaction.transaction_type == models.TransactionType.INVESTMENT
            )
            .scalar()
        )
        stats["total_investment"] = float(total_investment or 0.0)
    except SQLAlchemyError as e:
        logger.error("Failed to sum investment amount", exc_info=e)

    return stats
