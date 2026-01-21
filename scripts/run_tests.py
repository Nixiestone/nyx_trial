"""
Complete Production Test Suite
Tests all critical components before deployment

Author: Elite QDev Team
Location: scripts/run_tests.py (CREATE NEW FILE)
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import os
from datetime import datetime


class TestRunner:
    """Comprehensive test runner for production deployment."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
    
    def print_header(self, title):
        """Print test section header."""
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)
    
    def test_pass(self, test_name):
        """Mark test as passed."""
        self.passed += 1
        print(f"✅ PASS: {test_name}")
    
    def test_fail(self, test_name, error):
        """Mark test as failed."""
        self.failed += 1
        print(f"❌ FAIL: {test_name}")
        print(f"   Error: {error}")
    
    def test_warn(self, test_name, warning):
        """Mark test with warning."""
        self.warnings += 1
        print(f"⚠️  WARN: {test_name}")
        print(f"   Warning: {warning}")
    
    def test_environment(self):
        """Test 1: Environment Configuration."""
        self.print_header("TEST 1: ENVIRONMENT CONFIGURATION")
        
        # Check MASTER_KEY
        master_key = os.getenv('MASTER_KEY')
        if master_key:
            if len(master_key) >= 16:
                self.test_pass("MASTER_KEY set (16+ chars)")
            else:
                self.test_warn("MASTER_KEY set but short", "Use 32+ characters for production")
        else:
            self.test_fail("MASTER_KEY", "Not set. Required for encryption")
        
        # Check Python version
        import sys
        py_version = sys.version_info
        if py_version.major == 3 and py_version.minor >= 10:
            self.test_pass(f"Python version {py_version.major}.{py_version.minor}")
        else:
            self.test_fail("Python version", f"Need Python 3.10+, got {py_version.major}.{py_version.minor}")
        
        # Check required directories
        for dir_name in ['data', 'logs', 'models']:
            dir_path = Path(dir_name)
            if dir_path.exists():
                self.test_pass(f"Directory exists: {dir_name}/")
            else:
                self.test_warn(f"Directory missing: {dir_name}/", "Will be created automatically")
    
    def test_configuration(self):
        """Test 2: Configuration Files."""
        self.print_header("TEST 2: CONFIGURATION FILES")
        
        try:
            from config.settings import settings, validate_settings
            self.test_pass("Settings module import")
            
            # Validate settings
            if validate_settings():
                self.test_pass("Configuration validation")
            else:
                self.test_fail("Configuration validation", "Check config/secrets.env")
            
            # Check critical settings
            if settings.TELEGRAM_BOT_TOKEN:
                self.test_pass("Telegram bot token configured")
            else:
                self.test_fail("Telegram bot token", "Not set in secrets.env")
            
            if settings.MT5_LOGIN and settings.MT5_LOGIN > 0:
                self.test_pass("MT5 login configured")
            else:
                self.test_fail("MT5 login", "Not set in secrets.env")
            
        except Exception as e:
            self.test_fail("Configuration import", str(e))
    
    def test_database(self):
        """Test 3: Database Connectivity."""
        self.print_header("TEST 3: DATABASE CONNECTIVITY")
        
        try:
            from config.settings import settings
            from src.database.models import Base, User
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            
            self.test_pass("Database models import")
            
            # Create engine
            engine = create_engine(settings.DATABASE_URL, echo=False)
            self.test_pass("Database engine created")
            
            # Test connection
            Session = sessionmaker(bind=engine)
            session = Session()
            
            try:
                session.query(User).first()
                self.test_pass("Database query successful")
            except Exception as e:
                self.test_warn("Database query", "Tables may not exist. Run scripts/init_database.py")
            finally:
                session.close()
            
        except Exception as e:
            self.test_fail("Database connectivity", str(e))
    
    def test_security(self):
        """Test 4: Security Components."""
        self.print_header("TEST 4: SECURITY COMPONENTS")
        
        try:
            from src.security.encryption import get_encryptor
            
            encryptor = get_encryptor()
            self.test_pass("Encryption module loaded")
            
            # Test encryption/decryption
            test_data = "test_password_123"
            encrypted = encryptor.encrypt(test_data)
            decrypted = encryptor.decrypt(encrypted)
            
            if decrypted == test_data:
                self.test_pass("Encryption/decryption working")
            else:
                self.test_fail("Encryption/decryption", "Data mismatch")
            
        except Exception as e:
            self.test_fail("Security components", str(e))
        
        try:
            from src.security.validator import InputValidator, RateLimiter
            
            validator = InputValidator()
            self.test_pass("Input validator loaded")
            
            rate_limiter = RateLimiter(max_calls=10, time_window=60)
            self.test_pass("Rate limiter loaded")
            
            # Test validation
            try:
                validator.validate_symbol("EURUSD")
                self.test_pass("Symbol validation working")
            except:
                self.test_fail("Symbol validation", "Validation failed")
            
        except Exception as e:
            self.test_fail("Validator/RateLimiter", str(e))
    
    def test_mt5_connection(self):
        """Test 5: MT5 Connectivity."""
        self.print_header("TEST 5: MT5 CONNECTIVITY")
        
        try:
            import MetaTrader5 as mt5
            self.test_pass("MetaTrader5 module import")
            
            from src.data.mt5_connector import MT5Connector
            from config.settings import settings
            
            connector = MT5Connector(settings)
            self.test_pass("MT5Connector instantiated")
            
            if connector.connect():
                self.test_pass("MT5 connection successful")
                
                account_info = connector.get_account_info()
                if account_info:
                    self.test_pass(f"MT5 account info retrieved (Balance: {account_info['balance']})")
                else:
                    self.test_warn("MT5 account info", "Could not retrieve account data")
                
                connector.disconnect()
            else:
                self.test_fail("MT5 connection", "Could not connect. Check MT5 terminal and credentials")
            
        except Exception as e:
            self.test_fail("MT5 connectivity", str(e))
    
    def test_dependencies(self):
        """Test 6: Python Dependencies."""
        self.print_header("TEST 6: PYTHON DEPENDENCIES")
        
        critical_deps = [
            ('MetaTrader5', 'MetaTrader5'),
            ('telegram', 'python-telegram-bot'),
            ('sqlalchemy', 'SQLAlchemy'),
            ('cryptography', 'cryptography'),
            ('pandas', 'pandas'),
            ('numpy', 'numpy'),
            ('sklearn', 'scikit-learn'),
        ]
        
        for module_name, package_name in critical_deps:
            try:
                __import__(module_name)
                self.test_pass(f"Dependency: {package_name}")
            except ImportError:
                self.test_fail(f"Dependency: {package_name}", f"Install with: pip install {package_name}")
        
        # Optional dependencies
        optional_deps = [
            ('tensorflow', 'tensorflow'),
            ('xgboost', 'xgboost'),
        ]
        
        for module_name, package_name in optional_deps:
            try:
                __import__(module_name)
                self.test_pass(f"Optional: {package_name}")
            except ImportError:
                self.test_warn(f"Optional: {package_name}", "Not installed. Some ML features disabled")
    
    def test_telegram_bot(self):
        """Test 7: Telegram Bot Configuration."""
        self.print_header("TEST 7: TELEGRAM BOT")
        
        try:
            from telegram import Bot
            from config.settings import settings
            
            if not settings.TELEGRAM_BOT_TOKEN:
                self.test_fail("Telegram bot token", "Not configured")
                return
            
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            self.test_pass("Telegram Bot instantiated")
            
            # Test bot info retrieval (async)
            import asyncio
            
            async def test_bot():
                try:
                    me = await bot.get_me()
                    return True, me.username
                except Exception as e:
                    return False, str(e)
            
            success, result = asyncio.run(test_bot())
            
            if success:
                self.test_pass(f"Telegram Bot verified (@{result})")
            else:
                self.test_fail("Telegram Bot verification", result)
            
        except Exception as e:
            self.test_fail("Telegram Bot", str(e))
    
    def test_logging(self):
        """Test 8: Logging System."""
        self.print_header("TEST 8: LOGGING SYSTEM")
        
        try:
            from src.utils.logger import get_logger
            from config.settings import settings
            
            logger = get_logger("TestLogger", settings.LOG_LEVEL, settings.LOG_FILE_PATH)
            self.test_pass("Logger instantiated")
            
            # Test log writing
            logger.info("Test log entry")
            self.test_pass("Log writing successful")
            
            # Check log file
            log_file = Path(settings.LOG_FILE_PATH)
            if log_file.exists():
                self.test_pass(f"Log file created: {log_file}")
            else:
                self.test_warn("Log file", "Not created yet (will be created on first log)")
            
        except Exception as e:
            self.test_fail("Logging system", str(e))
    
    def run_all_tests(self):
        """Run all tests and generate report."""
        print("\n" + "=" * 70)
        print("NYX TRADING BOT - PRODUCTION TEST SUITE")
        print("=" * 70)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run all tests
        self.test_environment()
        self.test_configuration()
        self.test_database()
        self.test_security()
        self.test_dependencies()
        self.test_logging()
        self.test_telegram_bot()
        self.test_mt5_connection()
        
        # Final report
        print("\n" + "=" * 70)
        print("TEST RESULTS SUMMARY")
        print("=" * 70)
        print(f"✅ Passed:   {self.passed}")
        print(f"⚠️  Warnings: {self.warnings}")
        print(f"❌ Failed:   {self.failed}")
        print(f"Total:      {self.passed + self.warnings + self.failed}")
        
        if self.failed == 0:
            print("\n🎉 ALL CRITICAL TESTS PASSED!")
            print("\nYour bot is ready for deployment!")
            print("\nNext steps:")
            print("  1. Review any warnings above")
            print("  2. Run: python main.py (local test)")
            print("  3. Deploy to Render (production)")
            return True
        else:
            print("\n❌ TESTS FAILED!")
            print(f"\nPlease fix {self.failed} failed test(s) before deploying.")
            print("\nCommon fixes:")
            print("  - Set MASTER_KEY: [System.Environment]::SetEnvironmentVariable('MASTER_KEY', 'your-key', 'User')")
            print("  - Configure secrets.env with your MT5 and Telegram credentials")
            print("  - Install missing dependencies: pip install -r requirements.txt")
            print("  - Initialize database: python scripts/init_database.py")
            return False


if __name__ == "__main__":
    runner = TestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)