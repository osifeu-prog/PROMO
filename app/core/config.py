from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Basic App Settings
    PROJECT_NAME: str = "My FastAPI App"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: Optional[str] = None
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # Telegram Bot Settings from Railway
    BOT_TOKEN: str
    ADMIN_USER_ID: str
    PAYMENT_GROUP_ID: str
    COMMUNITY_GROUP_ID: str
    
    # FastAPI Docs
    DOCS_URL: str = "/docs"
    
    # Webhook
    WEBHOOK_URL: Optional[str] = None
    
    # Railway Environment
    RAILWAY_ENVIRONMENT: str = "production"
    RAILWAY_GIT_COMMIT_SHA: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
