"""
Database Models
Author: BLESSING OMOREGIE
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()


class Trade(Base):
    """Trade history model."""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    ticket = Column(Integer, unique=True)
    symbol = Column(String(20))
    direction = Column(String(10))
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    stop_loss = Column(Float)
    take_profit_1 = Column(Float)
    take_profit_2 = Column(Float)
    lot_size = Column(Float)
    profit = Column(Float, nullable=True)
    confidence = Column(Float)
    scenario = Column(String(50))
    ml_prediction = Column(Integer)
    sentiment_score = Column(Float)
    open_time = Column(DateTime, default=datetime.utcnow)
    close_time = Column(DateTime, nullable=True)
    is_closed = Column(Boolean, default=False)
    

class DailyPerformance(Base):
    """Daily performance metrics."""
    __tablename__ = 'daily_performance'
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, unique=True)
    starting_balance = Column(Float)
    ending_balance = Column(Float)
    daily_pnl = Column(Float)
    trades_count = Column(Integer)
    winners = Column(Integer)
    losers = Column(Integer)
    win_rate = Column(Float)
    

def init_database(database_url: str):
    """Initialize database."""
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()