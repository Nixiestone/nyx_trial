"""
Trade Copier - Distributes signals to all active user accounts
Author: BLESSING OMOREGIE
"""

from sqlalchemy.orm import Session
from src.database.models import MT5Account, Trade, User
from src.core.account_manager import AccountManager
from src.trading.mt5_executor import MT5Executor
from src.utils.logger import get_logger
from typing import Dict, List
from datetime import datetime

logger = get_logger("TradeCopier")


class TradeCopier:
    """Copies trading signals to all active user accounts."""
    
    def __init__(self, config, db_session: Session):
        self.config = config
        self.db = db_session
        self.logger = logger
        self.account_manager = AccountManager(config, db_session)
    
    def distribute_signal(self, signal: Dict) -> Dict[int, bool]:
        """
        Distribute trading signal to all active accounts.
        
        Args:
            signal: Trading signal dictionary
            
        Returns:
            Dictionary mapping account_id to execution success status
        """
        results = {}
        
        # Get all accounts with auto-trade enabled
        active_accounts = self.db.query(MT5Account).filter_by(
            auto_trade_enabled=True,
            status='active'
        ).all()
        
        self.logger.info(
            f"Distributing signal for {signal['symbol']} to {len(active_accounts)} accounts"
        )
        
        for account in active_accounts:
            try:
                success = self._execute_for_account(account, signal)
                results[account.id] = success
                
                if success:
                    self.logger.info(f"Signal executed for account {account.id}")
                else:
                    self.logger.warning(f"Signal execution failed for account {account.id}")
            
            except Exception as e:
                self.logger.exception(
                    f"Error executing signal for account {account.id}: {e}"
                )
                results[account.id] = False
        
        return results
    
    def _execute_for_account(self, account: MT5Account, signal: Dict) -> bool:
        """Execute signal for a specific account."""
        try:
            # Get connector for this account
            connector = self.account_manager.get_connector(account.id)
            if not connector:
                return False
            
            # Create executor
            executor = MT5Executor(self.config, connector)
            
            # Calculate position size based on account settings
            lot_size = self._calculate_lot_size(account, signal)
            
            # Execute trade
            if signal.get('immediate_execution', True):
                result = executor.open_position(
                    symbol=signal['symbol'],
                    order_type=signal['direction'],
                    lot_size=lot_size,
                    stop_loss=signal['stop_loss'],
                    take_profit=signal['take_profit_1'],
                    comment=f"NYX AutoTrade"
                )
            else:
                result = executor.place_pending_order(
                    symbol=signal['symbol'],
                    order_type=signal['order_type_enum'],
                    lot_size=lot_size,
                    entry_price=signal['entry_price'],
                    stop_loss=signal['stop_loss'],
                    take_profit=signal['take_profit_1'],
                    comment=f"NYX AutoTrade Pending"
                )
            
            if result:
                # Record trade in database
                self._record_trade(account, signal, result, lot_size)
                return True
            
            return False
        
        except Exception as e:
            self.logger.exception(f"Execution error: {e}")
            return False
    
    def _calculate_lot_size(self, account: MT5Account, signal: Dict) -> float:
        """Calculate lot size adjusted for account currency and risk."""
        # Base calculation on account risk percentage
        connector = self.account_manager.get_connector(account.id)
        if not connector:
            return self.config.MIN_LOT_SIZE
        
        lot_size = connector.calculate_lot_size(
            signal['symbol'],
            account.risk_percentage,
            abs(signal['entry_price'] - signal['stop_loss']) * 10000
        )
        
        return lot_size
    
    def _record_trade(
        self,
        account: MT5Account,
        signal: Dict,
        execution_result: Dict,
        lot_size: float
    ):
        """Record executed trade in database."""
        try:
            trade = Trade(
                user_id=account.user_id,
                account_id=account.id,
                mt5_ticket=execution_result.get('ticket'),
                symbol=signal['symbol'],
                direction=signal['direction'],
                entry_price=signal['entry_price'],
                stop_loss=signal['stop_loss'],
                take_profit_1=signal['take_profit_1'],
                take_profit_2=signal['take_profit_2'],
                lot_size=lot_size,
                confidence=signal.get('confidence'),
                scenario=signal.get('scenario'),
                ml_prediction=signal.get('ml_prediction', {}).get('ensemble'),
                sentiment_score=signal.get('sentiment', {}).get('score'),
                open_time=datetime.utcnow()
            )
            
            self.db.add(trade)
            self.db.commit()
            
        except Exception as e:
            self.logger.exception(f"Error recording trade: {e}")