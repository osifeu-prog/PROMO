# SLH Ecosystem

אקוסיסטם דיגיטלי חדשני המשלב AI, בלוקצ'יין וכלכלה חברתית.

## 🚀 התקנה והפעלה

### דרישות מערכת
- Python 3.11+
- PostgreSQL (מומלץ) או SQLite

### התקנה

1. **שכפול הריפוזיטורי**
```bash
git clone <repository-url>
cd slh-ecosystem
התקנת תלויות

bash
pip install -r requirements.txt
הגדרת משתני סביבה
צור קובץ .env:

env
BOT_TOKEN=your_telegram_bot_token
WEBHOOK_URL=https://your-app-url.railway.app
DATABASE_URL=postgresql://user:pass@host:port/db
ENVIRONMENT=production
ADMIN_USER_ID=your_telegram_id
הפעלת האפליקציה

bash
uvicorn app.main:app --reload
📁 מבנה הפרויקט
text
app/
├── main.py              # FastAPI application
├── bot.py              # Telegram bot handlers
├── models.py           # SQLAlchemy models
├── schemas.py          # Pydantic schemas
├── crud.py             # Database operations
├── database.py         # Database configuration
└── utils.py            # Utility functions
🔧 API Endpoints
GET / - הפניה לדף הנחיתה

GET /health - בדיקת בריאות המערכת

GET /api/stats - סטטיסטיקות מערכת

POST /{BOT_TOKEN} - webhook לטלגרם בוט

🤖 Telegram Bot
הבוט תומך בפקודות:

/start - התחל שימוש

/stats - סטטיסטיקות אישיות

/login - התחברות כאדמין

/request_admin - בקשת הרשאות אדמין

🗄️ מסד נתונים
המערכת תומכת ב:

PostgreSQL (מומלץ ל-production)

SQLite (לפיתוח)

🌐 Deployment
Railway
bash
railway up
Docker
dockerfile
FROM python:3.11
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD uvicorn app.main:app --host=0.0.0.0 --port=$PORT
📞 תמיכה
לפרטים נוספים:

בוט טלגרם: @ICQ2_bot

text

## 🎯 **הערות חשובות:**

1. **כל הקבצים מתואמים** אחד עם השני
2. **טיפול בשגיאות** מלא בכל הפונקציות
3. **אבטחה** - ניהול סיסמאות עם bcrypt
4. **רספונסיביות** - עיצוב מותאם לכל המכשירים
5. **מוכנות ל-production** עם environment variables

הפרויקט מוכן להפעלה מיידית! פשוט הגדר את משתני הסביבה והפעל עם `uvicorn app.main:app --reload`.
