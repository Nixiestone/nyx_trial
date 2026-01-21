"""
Database Models - Multi-User Auto-Trading System
Production-Ready Schema

Author: BLESSING OMOREGIE
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class UserRole(enum.Enum):
    """User role enumeration."""
    ADMIN = "admin"
    USER = "user"
    BANNED = "banned"


class AccountStatus(enum.Enum):
    """MT5 account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    ERROR = "error"


class User(Base):
    """Telegram users with role-based access."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_chat_id = Column(Integer, unique=True, nullable=False, index=True)
    telegram_username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    notifications_enabled = Column(Boolean, default=True)
    auto_trade_enabled = Column(Boolean, default=False)
    
    # Relationships
    accounts = relationship("MT5Account", back_populates="user", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, chat_id={self.telegram_chat_id}, role={self.role.value})>"


class MT5Account(Base):
    """MT5 trading accounts linked to users."""
    __tablename__ = 'mt5_accounts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    account_name = Column(String(100), nullable=False)
    mt5_login = Column(Integer, nullable=False)
    mt5_server = Column(String(100), nullable=False)
    encrypted_password = Column(Text, nullable=False)  # Encrypted with Fernet
    account_currency = Column(String(10), default='USD')
    account_balance = Column(Float, default=0.0)
    account_equity = Column(Float, default=0.0)
    account_leverage = Column(Integer, default=1)
    status = Column(Enum(AccountStatus), default=AccountStatus.PENDING)
    auto_trade_enabled = Column(Boolean, default=False)
    risk_percentage = Column(Float, default=1.0)
    max_daily_loss_percent = Column(Float, default=5.0)
    max_open_positions = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_connected = Column(DateTime)
    last_error = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="accounts")
    trades = relationship("Trade", back_populates="account")
    
    def __repr__(self):
        return f"<MT5Account(id={self.id}, login={self.mt5_login}, user_id={self.user_id})>"


class Trade(Base):
    """Trade execution history."""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    account_id = Column(Integer, ForeignKey('mt5_accounts.id'), index=True)
    mt5_ticket = Column(Integer, unique=True)
    symbol = Column(String(20), nullable=False, index=True)
    direction = Column(String(10), nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    stop_loss = Column(Float, nullable=False)
    take_profit_1 = Column(Float, nullable=False)
    take_profit_2 = Column(Float, nullable=False)
    lot_size = Column(Float, nullable=False)
    profit = Column(Float, default=0.0)
    pips = Column(Float, default=0.0)
    confidence = Column(Float)
    scenario = Column(String(100))
    ml_prediction = Column(Integer)
    sentiment_score = Column(Float)
    open_time = Column(DateTime, default=datetime.utcnow, index=True)
    close_time = Column(DateTime)
    is_closed = Column(Boolean, default=False)
    close_reason = Column(String(50))  # TP1, TP2, SL, MANUAL
    
    # Relationships
    user = relationship("User", back_populates="trades")
    account = relationship("MT5Account", back_populates="trades")
    
    def __repr__(self):
        return f"<Trade(id={self.id}, symbol={self.symbol}, ticket={self.mt5_ticket})>"


class SignalHistory(Base):
    """Trading signal generation history."""
    __tablename__ = 'signal_history'
    
    id = Column(Integer, primary_key=True)
    signal_hash = Column(String(64), unique=True, index=True)
    symbol = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit_1 = Column(Float, nullable=False)
    take_profit_2 = Column(Float, nullable=False)
    scenario = Column(String(100))
    poi_type = Column(String(20))
    confidence = Column(Float)
    ml_prediction_ensemble = Column(Integer)
    sentiment_score = Column(Float)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    occurrence_count = Column(Integer, default=1)
    sent_to_users = Column(Integer, default=0)
    executed_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<SignalHistory(id={self.id}, symbol={self.symbol}, hash={self.signal_hash[:8]})>"


class DailyPerformance(Base):
    """Daily performance metrics per account."""
    __tablename__ = 'daily_performance'
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('mt5_accounts.id'), index=True)
    date = Column(DateTime, nullable=False, index=True)
    starting_balance = Column(Float, nullable=False)
    ending_balance = Column(Float, nullable=False)
    daily_pnl = Column(Float, nullable=False)
    daily_pnl_percent = Column(Float, nullable=False)
    trades_count = Column(Integer, default=0)
    winners = Column(Integer, default=0)
    losers = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    
    def __repr__(self):
        return f"<DailyPerformance(account_id={self.account_id}, date={self.date})>"


class BotConfiguration(Base):
    """Bot-wide configuration and settings."""
    __tablename__ = 'bot_configuration'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey('users.id'))
    
    def __repr__(self):
        return f"<BotConfiguration(key={self.key})>"


class AuditLog(Base):
    """Audit log for security and compliance."""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50))  # account, trade, config, etc.
    resource_id = Column(Integer)
    details = Column(Text)
    ip_address = Column(String(45))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, user_id={self.user_id})>"