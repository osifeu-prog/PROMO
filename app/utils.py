import hashlib
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext

# הגדרות הצפנה
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "your-secret-key-change-in-production"  # צריך להיות בסביבה
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    """הצפנת סיסמה"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """בדיקת סיסמה"""
    return pwd_context.verify(plain_password, hashed_password)

def generate_contract_hash(details: str) -> str:
    """יצירת hash ייחודי לחוזה"""
    timestamp = datetime.utcnow().isoformat()
    unique_string = f"{details}{timestamp}{secrets.token_hex(8)}"
    return hashlib.sha256(unique_string.encode()).hexdigest()

def generate_random_password(length: int = 12) -> str:
    """יצירת סיסמה אקראית"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """יצירת JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """אימות JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

def format_currency(amount: float, currency: str = "USD") -> str:
    """פורמט כסף"""
    if currency == "USD":
        return f"${amount:,.2f}"
    elif currency == "ILS":
        return f"₪{amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"

def sanitize_input(text: str, max_length: int = 1000) -> str:
    """ניקוי קלט משתמש"""
    if not text:
        return ""
    
    # הסרת תווים מסוכנים
    cleaned = text.replace('<', '&lt;').replace('>', '&gt;')
    cleaned = cleaned.replace('"', '&quot;').replace("'", '&#39;')
    
    # הגבלת אורך
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + "..."
    
    return cleaned

def calculate_investment_return(principal: float, rate: float, years: int) -> float:
    """חישוב תשואה על השקעה"""
    return principal * (1 + rate) ** years

def validate_email(email: str) -> bool:
    """ולדיציית אימייל בסיסית"""
    if not email or '@' not in email:
        return False
    return True

class RateLimiter:
    """Rate limiter בסיסי"""
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}
    
    def is_allowed(self, user_id: int) -> bool:
        """בדיקה אם משתמש יכול לבצע פעולה"""
        now = datetime.utcnow().timestamp()
        user_requests = self.requests.get(user_id, [])
        
        # הסרת בקשות ישנות
        user_requests = [req_time for req_time in user_requests 
                        if now - req_time < self.window_seconds]
        
        if len(user_requests) >= self.max_requests:
            return False
        
        user_requests.append(now)
        self.requests[user_id] = user_requests
        return True
