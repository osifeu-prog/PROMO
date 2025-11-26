import logging
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from app.core.config import settings

logger = logging.getLogger(__name__)

class TelegramBotService:
    def __init__(self):
        self.bot = None
        self.application = None
        
    async def initialize(self):
        """Initialize the Telegram bot"""
        if not settings.BOT_TOKEN:
            logger.warning("No BOT_TOKEN provided, skipping Telegram bot initialization")
            return
            
        try:
            self.application = Application.builder().token(settings.BOT_TOKEN).build()
            self.bot = self.application.bot
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            # Set webhook if WEBHOOK_URL is provided
            if settings.WEBHOOK_URL:
                webhook_url = f"{settings.WEBHOOK_URL}/webhook/telegram"
                await self.bot.set_webhook(webhook_url)
                logger.info(f"Webhook set to: {webhook_url}")
            else:
                logger.info("Running in polling mode")
                
            logger.info("✅ Telegram bot initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Telegram bot: {e}")
            raise

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        await update.message.reply_text(
            f"👋 Hello {user.first_name}!\n\n"
            f"Welcome to {settings.PROJECT_NAME}!\n"
            f"Version: {settings.VERSION}\n"
            f"Environment: {settings.RAILWAY_ENVIRONMENT}"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🤖 **Available Commands:**

/start - Start the bot
/help - Show this help message
/status - Check bot status

📊 **Bot Information:**
- Environment: {environment}
- Version: {version}
- Admin: {admin_id}
        """.format(
            environment=settings.RAILWAY_ENVIRONMENT,
            version=settings.VERSION,
            admin_id=settings.ADMIN_USER_ID
        )
        await update.message.reply_text(help_text)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages"""
        user_id = update.effective_user.id
        
        # Check if user is admin
        if str(user_id) == settings.ADMIN_USER_ID:
            await update.message.reply_text("✅ Admin command received")
        else:
            await update.message.reply_text("👋 Thanks for your message!")

    async def send_to_admin(self, message: str):
        """Send message to admin"""
        if self.bot and settings.ADMIN_USER_ID:
            try:
                await self.bot.send_message(chat_id=settings.ADMIN_USER_ID, text=message)
            except Exception as e:
                logger.error(f"Failed to send message to admin: {e}")

    async def send_to_payment_group(self, message: str):
        """Send message to payment group"""
        if self.bot and settings.PAYMENT_GROUP_ID:
            try:
                await self.bot.send_message(chat_id=settings.PAYMENT_GROUP_ID, text=message)
            except Exception as e:
                logger.error(f"Failed to send message to payment group: {e}")

    async def send_to_community_group(self, message: str):
        """Send message to community group"""
        if self.bot and settings.COMMUNITY_GROUP_ID:
            try:
                await self.bot.send_message(chat_id=settings.COMMUNITY_GROUP_ID, text=message)
            except Exception as e:
                logger.error(f"Failed to send message to community group: {e}")

# Global instance
telegram_bot = TelegramBotService()

async def initialize_bot():
    """Initialize the bot (called from main.py)"""
    await telegram_bot.initialize()

async def process_webhook(update_dict: dict):
    """Process webhook update"""
    if telegram_bot.application:
        update = Update.de_json(update_dict, telegram_bot.application.bot)
        await telegram_bot.application.process_update(update)
