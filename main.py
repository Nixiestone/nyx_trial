"""
NYX Trading Bot - Production Multi-User Auto-Trading System
Complete Implementation with Telegram Bot Integration

Author: BLESSING OMOREGIE
Version: 2.0.0 Production
"""

import sys
import asyncio
import signal
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import settings, validate_settings
from src.database.models import Base, User, MT5Account, UserRole
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram.ext import Application

# Import core modules
from src.utils.logger import get_logger

logger = get_logger("MainBot", settings.LOG_LEVEL, settings.LOG_FILE_PATH)


class ProductionTradingBot:
    """
    Production-grade multi-user trading bot with auto-trading capabilities.
    """
    
    def __init__(self):
        """Initialize the trading bot."""
        self.logger = logger
        self.running = False
        self.telegram_app = None
        self.db_session = None
        
        self.logger.info("=" * 70)
        self.logger.info("NYX TRADING BOT - PRODUCTION INITIALIZATION")
        self.logger.info(f"Version: {settings.APP_VERSION}")
        self.logger.info(f"Author: {settings.AUTHOR}")
        self.logger.info("=" * 70)
    
    async def initialize(self) -> bool:
        """Initialize all bot systems."""
        try:
            # Step 1: Validate configuration
            self.logger.info("[1/6] Validating configuration...")
            if not validate_settings():
                self.logger.error("Configuration validation failed")
                return False
            self.logger.info("Configuration valid")
            
            # Step 2: Initialize database
            self.logger.info("[2/6] Initializing database...")
            if not await self._init_database():
                return False
            self.logger.info("Database initialized")
            
            # Step 3: Initialize Telegram bot
            self.logger.info("[3/6] Initializing Telegram bot...")
            if not await self._init_telegram_bot():
                return False
            self.logger.info("Telegram bot initialized")
            
            # Step 4: Initialize security systems
            self.logger.info("[4/6] Initializing security systems...")
            if not await self._init_security():
                return False
            self.logger.info("Security systems initialized")
            
            # Step 5: Initialize trading systems
            self.logger.info("[5/6] Initializing trading systems...")
            if not await self._init_trading_systems():
                return False
            self.logger.info("Trading systems initialized")
            
            # Step 6: Start background tasks
            self.logger.info("[6/6] Starting background tasks...")
            if not await self._start_background_tasks():
                return False
            self.logger.info("Background tasks started")
            
            self.logger.info("=" * 70)
            self.logger.info("BOT INITIALIZATION COMPLETE")
            self.logger.info("=" * 70)
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Initialization error: {e}")
            return False
    
    async def _init_database(self) -> bool:
        """Initialize database connection and schema."""
        try:
            # Create engine
            engine = create_engine(
                settings.DATABASE_URL,
                echo=settings.DEBUG,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20
            )
            
            # Create all tables
            Base.metadata.create_all(engine)
            
            # Create session factory
            Session = sessionmaker(bind=engine)
            self.db_session = Session()
            
            # Create default admin user if not exists
            admin_chat_id = int(settings.TELEGRAM_CHAT_ID) if settings.TELEGRAM_CHAT_ID else None
            
            if admin_chat_id:
                admin = self.db_session.query(User).filter_by(
                    telegram_chat_id=admin_chat_id
                ).first()
                
                if not admin:
                    admin = User(
                        telegram_chat_id=admin_chat_id,
                        role=UserRole.ADMIN,
                        first_name="Admin",
                        is_active=True,
                        notifications_enabled=True
                    )
                    self.db_session.add(admin)
                    self.db_session.commit()
                    self.logger.info(f"Created admin user with chat_id: {admin_chat_id}")
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Database initialization error: {e}")
            return False
    
    async def _init_telegram_bot(self) -> bool:
        """Initialize Telegram bot application."""
        try:
            if not settings.ENABLE_TELEGRAM or not settings.TELEGRAM_BOT_TOKEN:
                self.logger.warning("Telegram bot disabled or token not configured")
                return True
            
            # Create application
            self.telegram_app = Application.builder().token(
                settings.TELEGRAM_BOT_TOKEN
            ).build()
            
            # Register command handlers
            from src.telegram_bot.handlers.user_commands import register_user_handlers
            from src.telegram_bot.handlers.admin_commands import register_admin_handlers
            from src.telegram_bot.handlers.account_commands import register_account_handlers
            from src.telegram_bot.handlers.trade_commands import register_trade_handlers
            
            register_user_handlers(self.telegram_app, self.db_session)
            register_admin_handlers(self.telegram_app, self.db_session)
            register_account_handlers(self.telegram_app, self.db_session)
            register_trade_handlers(self.telegram_app, self.db_session)
            
            self.logger.info("Telegram bot handlers registered")
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Telegram bot initialization error: {e}")
            return False
    
    async def _init_security(self) -> bool:
        """Initialize security systems."""
        try:
            # Initialize encryption
            from src.security.encryption import get_encryptor
            encryptor = get_encryptor()
            self.logger.info("Encryption system initialized")
            
            # Initialize rate limiter
            from src.security.validator import RateLimiter
            self.rate_limiter = RateLimiter(max_calls=10, time_window=60)
            self.logger.info("Rate limiter initialized")
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Security initialization error: {e}")
            return False
    
    async def _init_trading_systems(self) -> bool:
        """Initialize trading systems."""
        try:
            # Import trading modules
            from src.core.account_manager import AccountManager
            from src.core.trade_copier import TradeCopier
            from src.trading.signal_generator import SignalGenerator
            
            # Initialize account manager
            self.account_manager = AccountManager(settings, self.db_session)
            self.logger.info("Account manager initialized")
            
            # Initialize trade copier
            self.trade_copier = TradeCopier(settings, self.db_session)
            self.logger.info("Trade copier initialized")
            
            # Initialize signal generator (will be used in background tasks)
            self.logger.info("Trading systems ready")
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Trading systems initialization error: {e}")
            return False
    
    async def _start_background_tasks(self) -> bool:
        """Start all background tasks."""
        try:
            # Start Telegram bot polling in background
            if self.telegram_app:
                asyncio.create_task(self._run_telegram_bot())
            
            # Start signal scanner in background
            asyncio.create_task(self._run_signal_scanner())
            
            # Start account health checker in background
            asyncio.create_task(self._run_health_checker())
            
            # Start performance reporter in background
            asyncio.create_task(self._run_performance_reporter())
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Background tasks error: {e}")
            return False
    
    async def _run_telegram_bot(self):
        """Run Telegram bot polling loop."""
        try:
            self.logger.info("Starting Telegram bot polling...")
            await self.telegram_app.initialize()
            await self.telegram_app.start()
            await self.telegram_app.updater.start_polling(drop_pending_updates=True)
            self.logger.info("Telegram bot is now running")
            
            # Keep running
            while self.running:
                await asyncio.sleep(1)
            
            # Shutdown
            await self.telegram_app.updater.stop()
            await self.telegram_app.stop()
            await self.telegram_app.shutdown()
            
        except Exception as e:
            self.logger.exception(f"Telegram bot error: {e}")
    
    async def _run_signal_scanner(self):
        """Background task: Scan for trading signals."""
        self.logger.info("Starting signal scanner...")
        
        while self.running:
            try:
                # Wait for configured interval
                await asyncio.sleep(settings.MARKET_UPDATE_INTERVAL_MINUTES * 60)
                
                self.logger.info("Running signal scan...")
                
                # Generate signals
                # This will be implemented in the signal generator
                # and distributed via trade copier to all active accounts
                
                self.logger.info("Signal scan complete")
                
            except Exception as e:
                self.logger.exception(f"Signal scanner error: {e}")
                await asyncio.sleep(60)  # Wait before retry
    
    async def _run_health_checker(self):
        """Background task: Monitor account health."""
        self.logger.info("Starting health checker...")
        
        while self.running:
            try:
                # Check every 5 minutes
                await asyncio.sleep(300)
                
                # Check all active accounts
                active_accounts = self.db_session.query(MT5Account).filter_by(
                    status='active',
                    auto_trade_enabled=True
                ).all()
                
                for account in active_accounts:
                    # Verify connection and update status
                    # This will be implemented in account manager
                    pass
                
            except Exception as e:
                self.logger.exception(f"Health checker error: {e}")
                await asyncio.sleep(60)
    
    async def _run_performance_reporter(self):
        """Background task: Generate performance reports."""
        self.logger.info("Starting performance reporter...")
        
        while self.running:
            try:
                # Daily report at configured interval
                await asyncio.sleep(settings.PERFORMANCE_REPORT_INTERVAL_HOURS * 3600)
                
                # Generate and send reports
                # This will be implemented in reporting module
                
            except Exception as e:
                self.logger.exception(f"Performance reporter error: {e}")
                await asyncio.sleep(3600)
    
    async def run(self):
        """Main bot execution loop."""
        if not await self.initialize():
            self.logger.error("Initialization failed. Exiting.")
            return
        
        self.running = True
        
        self.logger.info("\n" + "=" * 70)
        self.logger.info("BOT IS NOW RUNNING")
        self.logger.info("=" * 70)
        self.logger.info("Press Ctrl+C to stop")
        self.logger.info("")
        
        try:
            # Keep main loop alive
            while self.running:
                await asyncio.sleep(1)
        
        except KeyboardInterrupt:
            self.logger.info("\nShutdown signal received (Ctrl+C)")
        
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown."""
        self.logger.info("\nInitiating graceful shutdown...")
        
        self.running = False
        
        # Wait for background tasks to complete
        await asyncio.sleep(2)
        
        # Close database session
        if self.db_session:
            self.db_session.close()
        
        self.logger.info("Shutdown complete")
        self.logger.info("=" * 70)


async def main():
    """Main entry point."""
    bot = ProductionTradingBot()
    await bot.run()


if __name__ == "__main__":
    # Run with asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)