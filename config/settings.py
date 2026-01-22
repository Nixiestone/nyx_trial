"""
Trading Bot Configuration Settings - MT5 Version
FIXED VERSION - Added MASTER_KEY field

Author: BLESSING OMOREGIE
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Main configuration class for the trading bot.
    Values are loaded from environment variables defined in secrets.env
    """
    
    # Application Settings
    APP_NAME: str = "NYX Trading Bot"
    APP_VERSION: str = "1.0.0"
    AUTHOR: str = "BLESSING OMOREGIE"
    GITHUB_USERNAME: str = "Nixiestone"
    
    # CRITICAL: Master Encryption Key
    MASTER_KEY: str = Field(default="", env="MASTER_KEY")
    
    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # Primary Trading Platform
    PRIMARY_PLATFORM: str = Field(default="mt5", env="PRIMARY_PLATFORM")
    
    # MT5 Settings
    MT5_LOGIN: int = Field(default=0, env="MT5_LOGIN")
    MT5_PASSWORD: str = Field(default="", env="MT5_PASSWORD")
    MT5_SERVER: str = Field(default="", env="MT5_SERVER")
    MT5_PATH: str = Field(default="", env="MT5_PATH")
    MT5_TIMEOUT: int = Field(default=60000, env="MT5_TIMEOUT")
    
    # Alternative Platforms (Optional)
    USE_BINANCE: bool = Field(default=False, env="USE_BINANCE")
    BINANCE_API_KEY: str = Field(default="", env="BINANCE_API_KEY")
    BINANCE_API_SECRET: str = Field(default="", env="BINANCE_API_SECRET")
    BINANCE_TESTNET: bool = Field(default=True, env="BINANCE_TESTNET")
    
    USE_DERIV: bool = Field(default=False, env="USE_DERIV")
    DERIV_API_TOKEN: str = Field(default="", env="DERIV_API_TOKEN")
    DERIV_APP_ID: str = Field(default="", env="DERIV_APP_ID")
    
    # Trading Pairs
    TRADING_SYMBOLS: List[str] = [
        "EURUSD",
        "GBPUSD",
        "USDJPY",
        "AUDUSD",
        "USDCAD",
        "GBPJPY",
        "XAUUSD",
        "US30",
        "BTCUSD"
    ]
    
    # Timeframes
    HTF_TIMEFRAME: str = "H4"
    HTF_TIMEFRAME_ALT: str = "D1"
    ITF_TIMEFRAME: str = "H1"
    ITF_TIMEFRAME_ALT: str = "M15"
    LTF_TIMEFRAME: str = "M15"
    LTF_TIMEFRAME_ALT: str = "M5"
    
    # MT5 Timeframe Mapping
    TIMEFRAME_MAP: Dict[str, int] = {
        "M1": 1,
        "M5": 5,
        "M15": 15,
        "M30": 30,
        "H1": 16385,
        "H4": 16388,
        "D1": 16408,
        "W1": 32769,
        "MN1": 49153
    }
    
    # Risk Management
    MAX_POSITION_SIZE_PERCENT: float = 2.0
    MAX_DAILY_LOSS_PERCENT: float = 5.0
    MAX_OPEN_POSITIONS: int = 3
    DEFAULT_LEVERAGE: int = 1
    
    # MT5 Lot Size
    MIN_LOT_SIZE: float = 0.01
    MAX_LOT_SIZE: float = 10.0
    LOT_STEP: float = 0.01
    RISK_PER_TRADE_PERCENT: float = 1.0
    
    # Stop Loss and Take Profit
    SL_PADDING_PIPS: float = 3.0
    MINIMUM_TP1_RR: float = 2.0
    PARTIAL_CLOSE_TP1_PERCENT: float = 50.0
    MOVE_SL_TO_BREAKEVEN_AT_TP1: bool = True
    
    # Machine Learning Settings
    ML_MODEL_1_TYPE: str = "random_forest"
    ML_MODEL_2_TYPE: str = "gradient_boosting"
    ML_MODEL_3_TYPE: str = "lstm"
    ML_ENSEMBLE_THRESHOLD: float = 0.6
    ML_RETRAIN_INTERVAL_HOURS: int = 24
    
    # Sentiment Analysis
    SENTIMENT_THRESHOLD_BULLISH: float = 0.6
    SENTIMENT_THRESHOLD_BEARISH: float = -0.6
    SENTIMENT_WEIGHT: float = 0.3
    
    # News Scraping
    NEWS_API_KEY: str = Field(default="", env="NEWS_API_KEY")
    NEWS_SOURCES: List[str] = [
        "forex-factory",
        "investing-com",
        "fxstreet",
        "dailyfx",
        "reuters",
        "bloomberg",
        "x(twitter)",
        "the-economist",
        "financial-times"
    ]
    NEWS_FETCH_INTERVAL_MINUTES: int = 60
    
    # Telegram Notifications
    TELEGRAM_BOT_TOKEN: str = Field(default="", env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: str = Field(default="", env="TELEGRAM_CHAT_ID")
    ENABLE_TELEGRAM: bool = Field(default=True, env="ENABLE_TELEGRAM")
    
    # Discord Notifications (Optional)
    DISCORD_WEBHOOK_URL: str = Field(default="", env="DISCORD_WEBHOOK_URL")
    ENABLE_DISCORD: bool = Field(default=False, env="ENABLE_DISCORD")
    
    # Email Notifications (Optional)
    ENABLE_EMAIL: bool = Field(default=False, env="ENABLE_EMAIL")
    EMAIL_SENDER: str = Field(default="", env="EMAIL_SENDER")
    EMAIL_PASSWORD: str = Field(default="", env="EMAIL_PASSWORD")
    EMAIL_RECIPIENT: str = Field(default="", env="EMAIL_RECIPIENT")
    EMAIL_SMTP_SERVER: str = Field(default="smtp.gmail.com", env="EMAIL_SMTP_SERVER")
    EMAIL_SMTP_PORT: int = Field(default=587, env="EMAIL_SMTP_PORT")
    
    # Database Settings
    DATABASE_URL: str = Field(
        default="sqlite:///./data/trading_bot.db",
        env="DATABASE_URL"
    )
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE_PATH: str = "logs/trading_bot.log"
    LOG_MAX_BYTES: int = 10485760
    LOG_BACKUP_COUNT: int = 5
    
    # Market Update Interval
    MARKET_UPDATE_INTERVAL_MINUTES: int = 60
    
    # Auto Trading
    AUTO_TRADING_ENABLED: bool = Field(default=False, env="AUTO_TRADING_ENABLED")
    
    # API Rate Limiting
    API_RATE_LIMIT_CALLS: int = 1200
    API_RATE_LIMIT_PERIOD: int = 60
    
    # SMC Strategy Parameters
    SMC_MSS_CONFIRMATION_CANDLES: int = 1
    SMC_BOS_DOUBLE_BREAK_REQUIRED: bool = True
    SMC_FVG_MIN_SIZE_PERCENT: float = 0.1
    SMC_OB_LOOKBACK_CANDLES: int = 150
    SMC_BB_LOOKBACK_CANDLES: int = 150
    
    # POI Selection Rules
    POI_REQUIRE_INDUCEMENT: bool = True
    POI_REQUIRE_UNMITIGATED: bool = True
    POI_SELECT_CLOSEST_TO_LIQUIDITY: bool = True
    
    # Model Paths
    MODEL_SAVE_PATH: Path = Path("models")
    DATA_SAVE_PATH: Path = Path("data")
    
    # Security Settings
    API_KEY_ENCRYPTION_ENABLED: bool = True
    REQUIRE_IP_WHITELIST: bool = False
    ALLOWED_IPS: List[str] = []
    
    # Performance Monitoring
    ENABLE_PERFORMANCE_TRACKING: bool = True
    PERFORMANCE_REPORT_INTERVAL_HOURS: int = 24
    
    # Backtesting
    BACKTEST_START_DATE: str = "2023-01-01"
    BACKTEST_END_DATE: str = "2024-01-01"
    BACKTEST_INITIAL_CAPITAL: float = 10000.0
    
    # MT5 Connection Settings
    MT5_ENABLE_EXPERT_ADVISOR: bool = Field(default=False, env="MT5_ENABLE_EXPERT_ADVISOR")
    MT5_MAGIC_NUMBER: int = Field(default=234000, env="MT5_MAGIC_NUMBER")
    MT5_DEVIATION: int = Field(default=20, env="MT5_DEVIATION")
    MT5_FILLING_MODE: str = Field(default="FOK", env="MT5_FILLING_MODE")
    
    class Config:
        env_file = "config/secrets.env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # CRITICAL FIX: Ignore extra fields from .env


# Create global settings instance
settings = Settings()


# Validation function
def validate_settings():
    """
    Validates that all required settings are properly configured.
    """
    errors = []
    warnings = []
    
    # Check MASTER_KEY
    if not settings.MASTER_KEY or len(settings.MASTER_KEY) < 16:
        errors.append("MASTER_KEY must be at least 16 characters")
    
    # Check MT5 credentials
    if settings.PRIMARY_PLATFORM == "mt5":
        if settings.MT5_LOGIN == 0:
            errors.append("MT5_LOGIN is not set in secrets.env")
        
        if not settings.MT5_PASSWORD:
            errors.append("MT5_PASSWORD is not set in secrets.env")
        
        if not settings.MT5_SERVER:
            errors.append("MT5_SERVER is not set in secrets.env")
        
        if not settings.MT5_PATH:
            warnings.append("MT5_PATH is not set. Auto-detection will be attempted.")
    
    # Check Telegram
    if settings.ENABLE_TELEGRAM:
        if not settings.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is not set but Telegram is enabled")
        if not settings.TELEGRAM_CHAT_ID:
            errors.append("TELEGRAM_CHAT_ID is not set but Telegram is enabled")
    
    # Check news API
    if not settings.NEWS_API_KEY:
        warnings.append("NEWS_API_KEY is not set. Sentiment analysis may be limited.")
    
    # Check trading symbols
    if not settings.TRADING_SYMBOLS:
        errors.append("TRADING_SYMBOLS list is empty")
    
    # Check risk management
    if settings.MAX_POSITION_SIZE_PERCENT > 10:
        warnings.append("MAX_POSITION_SIZE_PERCENT is too high (max recommended: 10%)")
    
    if settings.DEFAULT_LEVERAGE > 5:
        warnings.append("HIGH LEVERAGE DETECTED: This is risky.")
    
    # Warn if auto trading is enabled
    if settings.AUTO_TRADING_ENABLED:
        warnings.append("WARNING: AUTO_TRADING is ENABLED.")
    
    # Print results
    if errors:
        print("\n=== CONFIGURATION ERRORS ===")
        for error in errors:
            print(f"ERROR: {error}")
        print("===========================\n")
    
    if warnings:
        print("\n=== CONFIGURATION WARNINGS ===")
        for warning in warnings:
            print(f"WARNING: {warning}")
        print("==============================\n")
    
    if not errors:
        print("\n=== CONFIGURATION VALID ===")
        print(f"Environment: {settings.ENVIRONMENT}")
        print(f"Primary Platform: {settings.PRIMARY_PLATFORM}")
        print(f"MT5 Login: {settings.MT5_LOGIN}")
        print(f"MT5 Server: {settings.MT5_SERVER}")
        print(f"Auto Trading: {settings.AUTO_TRADING_ENABLED}")
        print(f"Trading Symbols: {len(settings.TRADING_SYMBOLS)}")
        print(f"Telegram Enabled: {settings.ENABLE_TELEGRAM}")
        print("===========================\n")
        return True
    
    return False


if __name__ == "__main__":
    if validate_settings():
        print("Configuration loaded successfully!")
    else:
        print("Please fix configuration errors before running the bot.")