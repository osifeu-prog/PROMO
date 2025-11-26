import logging

# יצירת logger בסיסי
logger = logging.getLogger("app")

def log_api_request(method: str, path: str, status_code: int, duration_ms: float):
    """לוג פשוט לבקשות API"""
    logger.info(f"API {method} {path} - {status_code} - {duration_ms}ms")
