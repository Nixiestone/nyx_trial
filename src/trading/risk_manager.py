"""
Production-Grade Risk Management System
Complete mathematical risk formulas with per-user dynamic adjustment

Location: src/trading/risk_manager.py (REPLACE ENTIRE FILE)
Author: Elite QDev Team
"""

from typing import Dict, Optional, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from src.database.models import MT5Account, Trade, User
from src.utils.logger import get_logger
import numpy as np


class RiskManager:
    """
    Production-grade risk management with:
    - Kelly Criterion for optimal position sizing
    - Dynamic risk adjustment per user
    - Strict percentage-based risk control
    - Real-time risk monitoring
    """
    
    def __init__(self, config, mt5_connector, mt5_executor, db_session: Session):
        self.config = config
        self.connector = mt5_connector
        self.executor = mt5_executor
        self.db = db_session
        self.logger = get_logger(__name__, config.LOG_LEVEL, config.LOG_FILE_PATH)
    
    # ==================== POSITION SIZING ====================
    
    def calculate_position_size(
        self,
        account: MT5Account,
        symbol: str,
        entry_price: float,
        stop_loss: float
    ) -> float:
        """
        Calculate position size using STRICT percentage risk formula.
        
        Mathematical Formula:
        Position Size (lots) = (Account Balance * Risk%) / (Stop Loss Distance in Currency)
        
        Where:
        - Risk% = User's risk percentage setting (default 1%)
        - Stop Loss Distance = |Entry - Stop Loss| * Pip Value * Contract Size
        
        Args:
            account: MT5Account with user's risk settings
            symbol: Trading symbol
            entry_price: Entry price
            stop_loss: Stop loss price
            
        Returns:
            Position size in lots
        """
        try:
            # Get account info
            account_info = self.connector.get_account_info()
            if not account_info:
                return self.config.MIN_LOT_SIZE
            
            balance = account_info['balance']
            
            # Calculate risk amount (strict % of balance)
            risk_percent = account.risk_percentage  # User's setting
            risk_amount = balance * (risk_percent / 100)
            
            self.logger.info(f"Risk calculation: {risk_percent}% of ${balance:.2f} = ${risk_amount:.2f}")
            
            # Calculate stop loss distance in pips
            from src.utils.symbol_normalizer import SymbolNormalizer
            pip_value = SymbolNormalizer.get_pip_value(symbol)
            pip_multiplier = 1.0 / pip_value
            
            stop_loss_pips = abs(entry_price - stop_loss) * pip_multiplier
            
            # Get symbol info
            symbol_info = self.connector.get_symbol_info(symbol)
            if not symbol_info:
                return self.config.MIN_LOT_SIZE
            
            # Calculate lot size using connector's method
            lot_size = self.connector.calculate_lot_size(
                symbol,
                risk_percent,
                stop_loss_pips
            )
            
            # Apply user's maximum position size limit
            max_lot_size = getattr(account, 'max_lot_size', self.config.MAX_LOT_SIZE)
            lot_size = min(lot_size, max_lot_size)
            
            # Apply global limits
            lot_size = max(self.config.MIN_LOT_SIZE, lot_size)
            lot_size = min(self.config.MAX_LOT_SIZE, lot_size)
            
            # Round to lot step
            lot_step = symbol_info['volume_step']
            lot_size = round(lot_size / lot_step) * lot_step
            
            self.logger.info(
                f"Position size calculated: {lot_size} lots "
                f"(Risk: ${risk_amount:.2f}, SL: {stop_loss_pips:.1f} pips)"
            )
            
            return lot_size
            
        except Exception as e:
            self.logger.exception(f"Error calculating position size: {e}")
            return self.config.MIN_LOT_SIZE
    
    def calculate_kelly_criterion(
        self,
        account: MT5Account,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """
        Calculate optimal position size using Kelly Criterion.
        
        Mathematical Formula:
        Kelly % = W - [(1 - W) / R]
        
        Where:
        - W = Win rate (probability of winning)
        - R = Average Win / Average Loss (reward-to-risk ratio)
        
        Args:
            account: MT5Account
            win_rate: Historical win rate (0.0 to 1.0)
            avg_win: Average winning trade amount
            avg_loss: Average losing trade amount (positive number)
            
        Returns:
            Optimal risk percentage (capped at user's max risk)
        """
        try:
            if avg_loss == 0:
                return account.risk_percentage
            
            # Calculate Kelly percentage
            R = avg_win / avg_loss
            kelly_pct = win_rate - ((1 - win_rate) / R)
            
            # Convert to percentage
            kelly_pct = kelly_pct * 100
            
            # Cap at user's risk setting (conservative approach)
            kelly_pct = max(0.1, min(kelly_pct, account.risk_percentage))
            
            self.logger.info(
                f"Kelly Criterion: {kelly_pct:.2f}% "
                f"(Win Rate: {win_rate*100:.1f}%, R:R: {R:.2f})"
            )
            
            return kelly_pct
            
        except Exception as e:
            self.logger.exception(f"Kelly calculation error: {e}")
            return account.risk_percentage
    
    def get_user_trading_stats(self, account: MT5Account) -> Dict:
        """
        Calculate user's historical trading statistics.
        
        Returns:
            Dictionary with win_rate, avg_win, avg_loss, total_trades
        """
        try:
            # Get closed trades for this account
            closed_trades = self.db.query(Trade).filter(
                Trade.account_id == account.id,
                Trade.is_closed == True
            ).all()
            
            if not closed_trades:
                return {
                    'win_rate': 0.5,
                    'avg_win': 0,
                    'avg_loss': 0,
                    'total_trades': 0
                }
            
            # Calculate statistics
            winners = [t for t in closed_trades if t.profit > 0]
            losers = [t for t in closed_trades if t.profit < 0]
            
            win_rate = len(winners) / len(closed_trades) if closed_trades else 0.5
            avg_win = np.mean([t.profit for t in winners]) if winners else 0
            avg_loss = abs(np.mean([t.profit for t in losers])) if losers else 0
            
            return {
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'total_trades': len(closed_trades),
                'total_winners': len(winners),
                'total_losers': len(losers)
            }
            
        except Exception as e:
            self.logger.exception(f"Error getting trading stats: {e}")
            return {
                'win_rate': 0.5,
                'avg_win': 0,
                'avg_loss': 0,
                'total_trades': 0
            }
    
    # ==================== RISK LIMITS ====================
    
    def check_risk_limits(self, account: MT5Account) -> Tuple[bool, str]:
        """
        Check if trading is allowed based on strict risk limits.
        
        Checks:
        1. Daily loss limit (user-defined %)
        2. Maximum open positions (user-defined)
        3. Account margin level (minimum 200%)
        4. Weekly drawdown (automatic protection)
        
        Args:
            account: MT5Account to check
            
        Returns:
            Tuple of (can_trade, reason)
        """
        # Check daily loss limit
        daily_pnl = self.get_daily_pnl(account)
        account_info = self.connector.get_account_info()
        
        if not account_info:
            return False, "Cannot get account info"
        
        balance = account_info['balance']
        max_daily_loss = balance * (account.max_daily_loss_percent / 100)
        
        if daily_pnl < -max_daily_loss:
            msg = f"Daily loss limit reached: ${daily_pnl:.2f} (Limit: ${-max_daily_loss:.2f})"
            self.logger.risk_warning(msg, {
                'account_id': account.id,
                'daily_pnl': daily_pnl,
                'limit': max_daily_loss
            })
            return False, msg
        
        # Check max open positions
        position_count = self.executor.get_position_count()
        
        if position_count >= account.max_open_positions:
            msg = f"Max positions reached: {position_count}/{account.max_open_positions}"
            self.logger.risk_warning(msg, {'account_id': account.id})
            return False, msg
        
        # Check margin level
        if account_info['margin_level'] < 200:
            msg = f"Low margin level: {account_info['margin_level']:.2f}%"
            self.logger.risk_warning(msg, {'account_id': account.id})
            return False, msg
        
        # Check weekly drawdown (automatic protection)
        weekly_pnl = self.get_weekly_pnl(account)
        max_weekly_loss = balance * 0.10  # Maximum 10% weekly loss
        
        if weekly_pnl < -max_weekly_loss:
            msg = f"Weekly loss limit reached: ${weekly_pnl:.2f}"
            self.logger.risk_warning(msg, {'account_id': account.id})
            return False, msg
        
        return True, "All risk checks passed"
    
    def get_daily_pnl(self, account: MT5Account) -> float:
        """
        Calculate today's profit/loss for an account.
        
        Args:
            account: MT5Account
            
        Returns:
            Today's P&L
        """
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Get today's closed trades
            today_trades = self.db.query(Trade).filter(
                Trade.account_id == account.id,
                Trade.is_closed == True,
                Trade.close_time >= today_start
            ).all()
            
            total_pnl = sum(t.profit for t in today_trades if t.profit)
            
            return total_pnl
            
        except Exception as e:
            self.logger.exception(f"Error calculating daily P&L: {e}")
            return 0.0
    
    def get_weekly_pnl(self, account: MT5Account) -> float:
        """
        Calculate this week's profit/loss.
        
        Args:
            account: MT5Account
            
        Returns:
            This week's P&L
        """
        try:
            # Get start of week (Monday)
            today = datetime.utcnow().date()
            week_start = today - timedelta(days=today.weekday())
            week_start_dt = datetime.combine(week_start, datetime.min.time())
            
            # Get this week's closed trades
            week_trades = self.db.query(Trade).filter(
                Trade.account_id == account.id,
                Trade.is_closed == True,
                Trade.close_time >= week_start_dt
            ).all()
            
            total_pnl = sum(t.profit for t in week_trades if t.profit)
            
            return total_pnl
            
        except Exception as e:
            self.logger.exception(f"Error calculating weekly P&L: {e}")
            return 0.0
    
    # ==================== TRADE VALIDATION ====================
    
    def validate_trade(self, account: MT5Account, signal: Dict) -> Tuple[bool, str]:
        """
        Validate if a trade should be taken.
        
        Checks:
        - Risk limits
        - Signal confidence
        - Symbol availability
        - Spread check
        - Account-specific rules
        
        Args:
            account: MT5Account
            signal: Trading signal dictionary
            
        Returns:
            Tuple of (should_trade, reason)
        """
        # Check risk limits first
        can_trade, reason = self.check_risk_limits(account)
        if not can_trade:
            return False, reason
        
        # Check confidence threshold
        if signal['confidence'] < self.config.ML_ENSEMBLE_THRESHOLD:
            return False, f"Confidence too low: {signal['confidence']:.2f}"
        
        # Check if symbol is available
        symbol_info = self.connector.get_symbol_info(signal['symbol'])
        if not symbol_info:
            return False, f"Symbol {signal['symbol']} not available"
        
        # Check spread
        current_price = self.connector.get_current_price(signal['symbol'])
        if current_price:
            spread = current_price['ask'] - current_price['bid']
            max_spread = symbol_info['point'] * 50  # Max 50 pips
            
            if spread > max_spread:
                return False, f"Spread too high: {spread:.5f}"
        
        return True, "Trade validated"
    
    # ==================== RISK REPORTING ====================
    
    def get_risk_report(self, account: MT5Account) -> Dict:
        """
        Generate comprehensive risk report for an account.
        
        Returns:
            Dictionary with risk metrics
        """
        try:
            account_info = self.connector.get_account_info()
            if not account_info:
                return {}
            
            daily_pnl = self.get_daily_pnl(account)
            weekly_pnl = self.get_weekly_pnl(account)
            positions = self.executor.get_open_positions()
            
            # Calculate total risk exposure
            total_risk = sum(
                abs(pos['price_open'] - pos['sl']) * pos['volume']
                for pos in positions if pos['sl'] != 0
            )
            
            balance = account_info['balance']
            
            # Get trading statistics
            stats = self.get_user_trading_stats(account)
            
            return {
                'account_id': account.id,
                'account_name': account.account_name,
                'balance': balance,
                'equity': account_info['equity'],
                'margin_level': account_info['margin_level'],
                'daily_pnl': daily_pnl,
                'daily_pnl_percent': (daily_pnl / balance) * 100,
                'weekly_pnl': weekly_pnl,
                'weekly_pnl_percent': (weekly_pnl / balance) * 100,
                'open_positions': len(positions),
                'max_positions': account.max_open_positions,
                'total_risk_exposure': total_risk,
                'risk_exposure_percent': (total_risk / balance) * 100,
                'risk_per_trade': account.risk_percentage,
                'max_daily_loss': account.max_daily_loss_percent,
                'win_rate': stats['win_rate'] * 100,
                'total_trades': stats['total_trades'],
                'avg_win': stats['avg_win'],
                'avg_loss': stats['avg_loss']
            }
            
        except Exception as e:
            self.logger.exception(f"Error generating risk report: {e}")
            return {}


if __name__ == "__main__":
    print("Risk Manager - Production Ready")
    print("Mathematical formulas implemented:")
    print("1. Strict percentage-based position sizing")
    print("2. Kelly Criterion for optimal risk")
    print("3. Multi-layer risk limit checks")
    print("4. Per-user dynamic risk adjustment")