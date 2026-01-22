"""
Telegram Bot Main Module
Standalone Telegram bot that can run independently

Author: BLESSING OMOREGIE
Location: src/telegram_bot/bot.py
"""

import asyncio
from telegram.ext import Application
from sqlalchemy.orm import Session

from config.settings import settings
from config.database import get_db_session, init_database
from src.telegram_bot.handlers.user_commands import register_user_handlers
from src.telegram_bot.handlers.admin_commands import register_admin_handlers
from src.telegram_bot.handlers.account_commands import register_account_handlers
from src.telegram_bot.handlers.trade_commands import register_trade_handlers
from src.telegram_bot.handlers.button_handlers import register_button_handlers
from src.telegram_bot.handlers.missing_commands import register_missing_handlers
from src.utils.logger import get_logger

logger = get_logger("TelegramBot", settings.LOG_LEVEL, settings.LOG_FILE_PATH)


class TelegramBot:
    """
    Standalone Telegram Bot for trading notifications and control.
    Can run independently from main.py
    """
    
    def __init__(self, db_session: Session = None):
        self.db_session = db_session or get_db_session()
        self.application = None
        self.logger = logger
    
    def setup(self):
        """Setup bot with all handlers."""
        
        if not settings.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN not set in configuration")
        
        # Create application
        self.application = Application.builder().token(
            settings.TELEGRAM_BOT_TOKEN
        ).build()
        
        # Register all handlers
        self.logger.info("Registering command handlers...")
        
        register_user_handlers(self.application, self.db_session)
        register_admin_handlers(self.application, self.db_session)
        register_account_handlers(self.application, self.db_session)
        register_trade_handlers(self.application, self.db_session)
        register_button_handlers(self.application, self.db_session)
        register_missing_handlers(self.application, self.db_session)
        
        self.logger.info("All handlers registered successfully")
        
        return self.application
    
    async def start(self):
        """Start the bot."""
        
        if not self.application:
            self.setup()
        
        self.logger.info("Starting Telegram bot...")
        
        # Initialize and start
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)
        
        self.logger.info("✓ Telegram bot is running")
        
        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            self.logger.info("Shutdown signal received")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the bot."""
        
        self.logger.info("Stopping Telegram bot...")
        
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
        
        if self.db_session:
            self.db_session.close()
        
        self.logger.info("✓ Telegram bot stopped")


async def main():
    """Run bot standalone."""
    
    # Initialize database
    init_database()
    
    # Create and run bot
    bot = TelegramBot()
    await bot.start()


if __name__ == "__main__":
    print("=" * 70)
    print("NIXIE TRADES TELEGRAM BOT - STANDALONE MODE")
    print("=" * 70)
    print("\nStarting bot...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nBot stopped by user")