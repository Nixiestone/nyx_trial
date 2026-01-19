"""
Risk Management Module
Author: BLESSING OMOREGIE
GitHub: Nixiestone
Repository: nyx_trial
"""

from typing import Dict, Optional, Tuple
from datetime import datetime, date
from ..utils.logger import get_logger


class RiskManager:
    """Manages trading risk and position sizing."""
    
    def __init__(self, config, mt5_connector, mt5_executor):
        self.config = config
        self.connector = mt5_connector
        self.executor = mt5_executor
        self.logger = get_logger(__name__, config.LOG_LEVEL, config.LOG_FILE_PATH)
    
    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        account_balance: Optional[float] = None
    ) -> float:
        """Calculate appropriate position size."""
        
        try:
            if account_balance is None:
                account_info = self.connector.get_account_info()
                if not account_info:
                    return self.config.MIN_LOT_SIZE
                account_balance = account_info['balance']
            
            # Calculate risk amount
            risk_amount = account_balance * (self.config.RISK_PER_TRADE_PERCENT / 100)
            
            # Calculate pips
            stop_loss_pips = abs(entry_price - stop_loss) * 10000
            
            # Get symbol info
            symbol_info = self.connector.get_symbol_info(symbol)
            if not symbol_info:
                return self.config.MIN_LOT_SIZE
            
            # Calculate lot size
            lot_size = self.connector.calculate_lot_size(
                symbol,
                self.config.RISK_PER_TRADE_PERCENT,
                stop_loss_pips
            )
            
            # Apply limits
            lot_size = max(self.config.MIN_LOT_SIZE, lot_size)
            lot_size = min(self.config.MAX_LOT_SIZE, lot_size)
            
            self.logger.info(f"Position size for {symbol}: {lot_size} lots")
            
            return lot_size
            
        except Exception as e:
            self.logger.exception(f"Error calculating position size: {e}")
            return self.config.MIN_LOT_SIZE
    
    def check_risk_limits(self) -> Tuple[bool, str]:
        """Check if trading is allowed based on risk limits."""
        
        # Check daily loss limit
        daily_pnl = self.executor.get_daily_profit()
        account_info = self.connector.get_account_info()
        
        if not account_info:
            return False, "Cannot get account info"
        
        max_daily_loss = account_info['balance'] * (self.config.MAX_DAILY_LOSS_PERCENT / 100)
        
        if daily_pnl < -max_daily_loss:
            msg = f"Daily loss limit reached: {daily_pnl:.2f}"
            self.logger.risk_warning(msg, {'daily_pnl': daily_pnl, 'limit': max_daily_loss})
            return False, msg
        
        # Check max open positions
        position_count = self.executor.get_position_count()
        
        if position_count >= self.config.MAX_OPEN_POSITIONS:
            msg = f"Max positions reached: {position_count}/{self.config.MAX_OPEN_POSITIONS}"
            self.logger.risk_warning(msg, {'count': position_count})
            return False, msg
        
        # Check account margin
        if account_info['margin_level'] < 200:
            msg = f"Low margin level: {account_info['margin_level']:.2f}%"
            self.logger.risk_warning(msg, account_info)
            return False, msg
        
        return True, "All risk checks passed"
    
    def validate_trade(self, signal: Dict) -> Tuple[bool, str]:
        """Validate if a trade should be taken."""
        
        # Check risk limits
        can_trade, reason = self.check_risk_limits()
        if not can_trade:
            return False, reason
        
        # Check confidence threshold
        if signal['confidence'] < self.config.ML_ENSEMBLE_THRESHOLD:
            return False, f"Confidence too low: {signal['confidence']:.2f}"
        
        # Check if symbol is tradeable
        symbol_info = self.connector.get_symbol_info(signal['symbol'])
        if not symbol_info:
            return False, f"Symbol {signal['symbol']} not available"
        
        # Check spread
        current_price = self.connector.get_current_price(signal['symbol'])
        if current_price:
            spread = current_price['ask'] - current_price['bid']
            max_spread = symbol_info['point'] * 50  # Max 50 pips spread
            
            if spread > max_spread:
                return False, f"Spread too high: {spread}"
        
        return True, "Trade validated"
    
    def get_risk_report(self) -> Dict:
        """Generate risk management report."""
        
        account_info = self.connector.get_account_info()
        if not account_info:
            return {}
        
        daily_pnl = self.executor.get_daily_profit()
        positions = self.executor.get_open_positions()
        
        total_risk = sum(
            abs(pos['price_open'] - pos['sl']) * pos['volume']
            for pos in positions if pos['sl'] != 0
        )
        
        return {
            'balance': account_info['balance'],
            'equity': account_info['equity'],
            'margin_level': account_info['margin_level'],
            'daily_pnl': daily_pnl,
            'daily_pnl_percent': (daily_pnl / account_info['balance']) * 100,
            'open_positions': len(positions),
            'max_positions': self.config.MAX_OPEN_POSITIONS,
            'total_risk': total_risk,
            'risk_percent': (total_risk / account_info['balance']) * 100
        }


if __name__ == "__main__":
    print("Risk Manager module - use with MT5 connector")