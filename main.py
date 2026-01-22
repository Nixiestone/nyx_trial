"""
NYX Trading Bot - Production Main Entry Point
FULLY CORRECTED - No unused imports

Version: 2.0.3 Production
Author: BLESSING OMOREGIE
"""

import sys
import asyncio
import signal
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment FIRST
import load_environment
load_environment.load_environment()

# Import required modules only
from config.settings import settings, validate_settings
from src.database.models import Base, User, UserRole
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram.ext import Application

# Import handlers
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
    """Production-ready async trading bot with integrated health checks."""
    
    def __init__(self):
        self.logger = logger
        self.running = False
        self.telegram_app = None
        self.db_session = None
        self.message_queue = get_message_queue()
        self.mt5_connector = None
        self.shutdown_event = asyncio.Event()
        
        self.logger.info("="*70)
        self.logger.info("NYX TRADING BOT - PRODUCTION INITIALIZATION")
        self.logger.info(f"Version: {settings.APP_VERSION}")
        self.logger.info(f"Author: {settings.AUTHOR}")
        self.logger.info("="*70)
    
    async def _run_health_server(self):
        """Run health check HTTP server for Render.com monitoring."""
        from aiohttp import web
        
        async def health_check(request):
            """Health check endpoint - returns 200 if bot is running."""
            return web.json_response({
                "status": "healthy",
                "bot_running": self.running,
                "telegram_active": self.telegram_app is not None,
                "timestamp": datetime.utcnow().isoformat(),
                "service": "nyx-trading-bot"
            })
        
        async def root(request):
            """Root endpoint."""
            return web.Response(text="NYX Trading Bot - Production Running")
        
        app = web.Application()
        app.router.add_get('/health', health_check)
        app.router.add_get('/', root)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()
        
        self.logger.info("Health check server started on port 8080")
    
    async def initialize(self) -> bool:
        """Initialize all bot systems."""
        try:
            # Validate configuration
            self.logger.info("[1/6] Validating configuration...")
            if not validate_settings():
                self.logger.error("Configuration validation failed")
                return False
            
            # Initialize database
            self.logger.info("[2/6] Initializing database...")
            if not await self._init_database():
                return False
            
            # Initialize Telegram
            self.logger.info("[3/6] Initializing Telegram bot...")
            if not await self._init_telegram_bot():
                return False
            
            # Initialize security
            self.logger.info("[4/6] Initializing security...")
            if not await self._init_security():
                return False
            
            # Initialize trading systems
            self.logger.info("[5/6] Initializing trading systems...")
            if not await self._init_trading_systems():
                return False
            
            # Start background tasks
            self.logger.info("[6/6] Starting background tasks...")
            if not await self._start_background_tasks():
                return False
            
            self.logger.info("="*70)
            self.logger.info("BOT INITIALIZATION COMPLETE")
            self.logger.info("="*70)
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Initialization error: {e}")
            return False
    
    async def _init_database(self) -> bool:
        """Initialize database with error handling."""
        try:
            Path("data").mkdir(parents=True, exist_ok=True)
            
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
            
            await loop.run_in_executor(None, Base.metadata.create_all, engine)
            
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
                    self.logger.info(f"Created admin user: {admin_chat_id}")
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Database init error: {e}")
            return False
    
    async def _init_telegram_bot(self) -> bool:
        """Initialize Telegram bot."""
        try:
            if not settings.ENABLE_TELEGRAM or not settings.TELEGRAM_BOT_TOKEN:
                self.logger.warning("Telegram disabled")
                return True
            
            self.telegram_app = Application.builder().token(
                settings.TELEGRAM_BOT_TOKEN
            ).build()
            
            # Register handlers
            register_user_handlers(self.telegram_app, self.db_session)
            register_admin_handlers(self.telegram_app, self.db_session)
            register_account_handlers(self.telegram_app, self.db_session)
            register_trade_handlers(self.telegram_app, self.db_session)
            register_button_handlers(self.telegram_app, self.db_session)
            register_missing_handlers(self.telegram_app, self.db_session)
            
            self.logger.info("Telegram handlers registered")
            return True
            
        except Exception as e:
            self.logger.exception(f"Telegram init error: {e}")
            return False
    
    async def _init_security(self) -> bool:
        """Initialize security systems."""
        try:
            from src.security.encryption import get_encryptor
            encryptor = get_encryptor()
            self.logger.info("Encryption initialized")
            return True
        except Exception as e:
            self.logger.exception(f"Security init error: {e}")
            return False
    
    async def _init_trading_systems(self) -> bool:
        """Initialize trading systems."""
        try:
            from src.core.account_manager import AccountManager
            from src.data.mt5_connector import MT5Connector
            
            self.mt5_connector = MT5Connector(settings)
            self.account_manager = AccountManager(settings, self.db_session)
            
            self.logger.info("Trading systems initialized")
            return True
        except Exception as e:
            self.logger.exception(f"Trading init error: {e}")
            return False
    
    async def _start_background_tasks(self) -> bool:
        """Start async background tasks."""
        try:
            asyncio.create_task(self._run_health_server())
            asyncio.create_task(self._run_telegram_bot())
            asyncio.create_task(self._run_mt5_heartbeat())
            return True
        except Exception as e:
            self.logger.exception(f"Background tasks error: {e}")
            return False
    
    async def _run_telegram_bot(self):
        """Run Telegram bot."""
        try:
            if not self.telegram_app:
                return
            
            await self.telegram_app.initialize()
            await self.telegram_app.start()
            
            # Process queued messages
            stats = await self.message_queue.send_queued_messages(
                self.telegram_app.bot
            )
            if stats['sent'] > 0:
                self.logger.info(f"Sent {stats['sent']} queued messages")
            
            await self.telegram_app.updater.start_polling(
                drop_pending_updates=True
            )
            
            self.logger.info("Telegram bot running")
            await self.shutdown_event.wait()
            
            # Shutdown
            await self.telegram_app.updater.stop()
            await self.telegram_app.stop()
            await self.telegram_app.shutdown()
            
        except Exception as e:
            self.logger.exception(f"Telegram bot error: {e}")
    
    async def _run_mt5_heartbeat(self):
        """MT5 connection heartbeat."""
        self.logger.info("MT5 heartbeat started")
        
        while self.running:
            try:
                await asyncio.sleep(60)
                
                if self.mt5_connector and not self.mt5_connector.check_connection():
                    self.logger.warning("MT5 connection lost, reconnecting...")
                    if self.mt5_connector.connect():
                        self.logger.info("MT5 reconnected")
                
            except Exception as e:
                self.logger.exception(f"MT5 heartbeat error: {e}")
                await asyncio.sleep(60)
    
    async def run(self):
        """Main execution loop."""
        if not await self.initialize():
            self.logger.error("Initialization failed")
            return
        
        self.running = True
        
        self.logger.info("\n" + "="*70)
        self.logger.info("BOT IS NOW RUNNING")
        self.logger.info("="*70)
        self.logger.info("Press Ctrl+C to stop\n")
        
        try:
            await self.shutdown_event.wait()
        except KeyboardInterrupt:
            self.logger.info("\nShutdown signal received")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown."""
        self.logger.info("Shutting down...")
        
        self.running = False
        self.shutdown_event.set()
        
        await asyncio.sleep(2)
        
        if self.db_session:
            self.db_session.close()
        
        if self.mt5_connector:
            self.mt5_connector.disconnect()
        
        self.logger.info("Shutdown complete")


async def main():
    """Async main entry point."""
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