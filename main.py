"""
NYX Trading Bot - Production Main Entry Point
FIXED VERSION - Correct Import Order

Version: 2.0.1 Production
Author: BLESSING OMOREGIE (Fixed by Elite QDev Team)
"""

import sys
import asyncio
import signal
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# CRITICAL: Load environment variables FIRST
import load_env
load_env.load_environment()

# Now import everything else
from config.settings import settings, validate_settings
from src.database.models import Base, User, MT5Account, UserRole, AccountStatus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram.ext import Application

# Import all handlers
from src.utils.logger import get_logger
from src.telegram_bot.handlers.user_commands import register_user_handlers
from src.telegram_bot.handlers.admin_commands import register_admin_handlers
from src.telegram_bot.handlers.account_commands import register_account_handlers
from src.telegram_bot.handlers.trade_commands import register_trade_handlers
from src.telegram_bot.handlers.button_handlers import register_button_handlers
from src.telegram_bot.handlers.missing_commands import register_missing_handlers
from src.telegram_bot.message_queue import get_message_queue

logger = get_logger("MainBot", settings.LOG_LEVEL, settings.LOG_FILE_PATH)


class ProductionTradingBot:
    """
    Production-grade async trading bot with:
    - Non-blocking asyncio operations
    - MT5 auto-reconnect heartbeat
    - Graceful shutdown
    - Message queue for offline resilience
    """
    
    def __init__(self):
        self.logger = logger
        self.running = False
        self.telegram_app = None
        self.db_session = None
        self.message_queue = get_message_queue()
        self.mt5_connector = None
        self.shutdown_event = asyncio.Event()
        
        self.logger.info("=" * 70)
        self.logger.info("NYX TRADING BOT - PRODUCTION INITIALIZATION")
        self.logger.info(f"Version: {settings.APP_VERSION}")
        self.logger.info(f"Author: {settings.AUTHOR}")
        self.logger.info("=" * 70)
    
    async def initialize(self) -> bool:
        """Initialize all bot systems asynchronously"""
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
        """Initialize database with proper async handling"""
        try:
            Path("data").mkdir(parents=True, exist_ok=True)
            
            # Create engine (synchronous but in executor)
            loop = asyncio.get_event_loop()
            engine = await loop.run_in_executor(
                None,
                lambda: create_engine(
                    settings.DATABASE_URL,
                    echo=settings.DEBUG,
                    pool_pre_ping=True,
                    pool_size=10,
                    max_overflow=20
                )
            )
            
            # Create tables
            await loop.run_in_executor(None, Base.metadata.create_all, engine)
            
            # Create session
            Session = sessionmaker(bind=engine)
            self.db_session = Session()
            
            # Create admin user if needed
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
        """Initialize Telegram bot with all handlers"""
        try:
            if not settings.ENABLE_TELEGRAM or not settings.TELEGRAM_BOT_TOKEN:
                self.logger.warning("Telegram bot disabled")
                return True
            
            self.telegram_app = Application.builder().token(
                settings.TELEGRAM_BOT_TOKEN
            ).build()
            
            # Register ALL handlers
            self.logger.info("Registering command handlers...")
            
            register_user_handlers(self.telegram_app, self.db_session)
            self.logger.info("  - User commands registered")
            
            register_admin_handlers(self.telegram_app, self.db_session)
            self.logger.info("  - Admin commands registered")
            
            register_account_handlers(self.telegram_app, self.db_session)
            self.logger.info("  - Account commands registered")
            
            register_trade_handlers(self.telegram_app, self.db_session)
            self.logger.info("  - Trade commands registered")
            
            register_button_handlers(self.telegram_app, self.db_session)
            self.logger.info("  - Button handlers registered")
            
            register_missing_handlers(self.telegram_app, self.db_session)
            self.logger.info("  - Missing commands registered")
            
            self.logger.info("All Telegram handlers registered")
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Telegram init error: {e}")
            return False
    
    async def _init_security(self) -> bool:
        """Initialize security systems"""
        try:
            from src.security.encryption import get_encryptor
            from src.security.validator import RateLimiter
            
            encryptor = get_encryptor()
            self.logger.info("Encryption system initialized")
            
            self.rate_limiter = RateLimiter(max_calls=10, time_window=60)
            self.logger.info("Rate limiter initialized")
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Security init error: {e}")
            return False
    
    async def _init_trading_systems(self) -> bool:
        """Initialize trading systems with MT5 connector"""
        try:
            from src.core.account_manager import AccountManager
            from src.core.trade_copier import TradeCopier
            from src.data.mt5_connector import MT5Connector
            
            # Initialize MT5 connector
            self.mt5_connector = MT5Connector(settings)
            self.logger.info("MT5 connector initialized")
            
            # Initialize account manager
            self.account_manager = AccountManager(settings, self.db_session)
            self.logger.info("Account manager initialized")
            
            # Initialize trade copier
            self.trade_copier = TradeCopier(settings, self.db_session)
            self.logger.info("Trade copier initialized")
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Trading systems init error: {e}")
            return False
    
    async def _start_background_tasks(self) -> bool:
        """Start all async background tasks"""
        try:
            # Start all background tasks concurrently
            asyncio.create_task(self._run_telegram_bot())
            asyncio.create_task(self._run_signal_scanner())
            asyncio.create_task(self._run_health_checker())
            asyncio.create_task(self._run_performance_reporter())
            asyncio.create_task(self._run_message_queue_processor())
            asyncio.create_task(self._run_mt5_heartbeat())
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Background tasks error: {e}")
            return False
    
    async def _run_telegram_bot(self):
        """Run Telegram bot polling loop (async)"""
        try:
            self.logger.info("Starting Telegram bot polling...")
            await self.telegram_app.initialize()
            await self.telegram_app.start()
            
            # Process queued messages
            self.logger.info("Processing queued messages...")
            stats = await self.message_queue.send_queued_messages(self.telegram_app.bot)
            if stats['sent'] > 0:
                self.logger.info(f"Sent {stats['sent']} queued messages")
            
            await self.telegram_app.updater.start_polling(drop_pending_updates=True)
            self.logger.info("Telegram bot is running")
            
            # Wait for shutdown
            await self.shutdown_event.wait()
            
            # Shutdown
            await self.telegram_app.updater.stop()
            await self.telegram_app.stop()
            await self.telegram_app.shutdown()
            
        except Exception as e:
            self.logger.exception(f"Telegram bot error: {e}")
    
    async def _run_mt5_heartbeat(self):
        """MT5 Auto-Reconnect Heartbeat"""
        self.logger.info("Starting MT5 heartbeat...")
        
        while self.running:
            try:
                await asyncio.sleep(60)
                
                if not self.mt5_connector:
                    continue
                
                if not self.mt5_connector.check_connection():
                    self.logger.warning("MT5 connection lost. Attempting reconnect...")
                    
                    if self.mt5_connector.connect():
                        self.logger.info("MT5 reconnected successfully")
                    else:
                        self.logger.error("MT5 reconnection failed. Will retry in 60s")
                
            except Exception as e:
                self.logger.exception(f"MT5 heartbeat error: {e}")
                await asyncio.sleep(60)
    
    async def _run_signal_scanner(self):
        """Background signal scanner (async)"""
        self.logger.info("Starting signal scanner...")
        
        while self.running:
            try:
                await asyncio.sleep(settings.MARKET_UPDATE_INTERVAL_MINUTES * 60)
                
                self.logger.info("Running signal scan...")
                # Signal generation logic here
                self.logger.info("Signal scan complete")
                
            except Exception as e:
                self.logger.exception(f"Signal scanner error: {e}")
                await asyncio.sleep(60)
    
    async def _run_health_checker(self):
        """Background health checker (async)"""
        self.logger.info("Starting health checker...")
        
        while self.running:
            try:
                await asyncio.sleep(300)
                
                active_accounts = self.db_session.query(MT5Account).filter_by(
                    status=AccountStatus.ACTIVE,
                    auto_trade_enabled=True
                ).all()
                
            except Exception as e:
                self.logger.exception(f"Health checker error: {e}")
                await asyncio.sleep(60)
    
    async def _run_performance_reporter(self):
        """Background performance reporter (async)"""
        self.logger.info("Starting performance reporter...")
        
        while self.running:
            try:
                await asyncio.sleep(settings.PERFORMANCE_REPORT_INTERVAL_HOURS * 3600)
                
            except Exception as e:
                self.logger.exception(f"Performance reporter error: {e}")
                await asyncio.sleep(3600)
    
    async def _run_message_queue_processor(self):
        """Background message queue processor (async)"""
        self.logger.info("Starting message queue processor...")
        
        while self.running:
            try:
                await asyncio.sleep(300)
                
                if self.telegram_app:
                    stats = await self.message_queue.send_queued_messages(self.telegram_app.bot)
                    if stats['sent'] > 0:
                        self.logger.info(f"Queue: {stats['sent']} sent, {stats['failed']} failed")
                
                import random
                if random.random() < 0.01:
                    deleted = self.message_queue.cleanup_old_messages(days=7)
                    if deleted > 0:
                        self.logger.info(f"Cleaned up {deleted} old messages")
                
            except Exception as e:
                self.logger.exception(f"Message queue error: {e}")
                await asyncio.sleep(60)
    
    async def run(self):
        """Main async execution loop"""
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
            await self.shutdown_event.wait()
        
        except KeyboardInterrupt:
            self.logger.info("\nShutdown signal received (Ctrl+C)")
        
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful async shutdown"""
        self.logger.info("\nInitiating graceful shutdown...")
        
        self.running = False
        self.shutdown_event.set()
        
        await asyncio.sleep(2)
        
        if self.db_session:
            self.db_session.close()
        
        if self.mt5_connector:
            self.mt5_connector.disconnect()
        
        queue_stats = self.message_queue.get_queue_stats()
        if queue_stats['pending'] > 0:
            self.logger.info(f"Shutdown: {queue_stats['pending']} messages queued")
        
        self.logger.info("Shutdown complete")
        self.logger.info("=" * 70)


async def main():
    """Async main entry point"""
    bot = ProductionTradingBot()
    
    def signal_handler(sig, frame):
        bot.shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)