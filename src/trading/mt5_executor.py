"""
MT5 Trade Execution Module - PRODUCTION READY
Author: BLESSING OMOREGIE
GitHub: Nixiestone
Repository: nyx_trial

COMPLETE AND ERROR-FREE VERSION
Handles trade execution and management on MT5.
"""

import MetaTrader5 as mt5
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum

from ..utils.logger import get_logger
from ..data.mt5_connector import MT5Connector


class OrderType(Enum):
    """Order type enumeration."""
    BUY = mt5.ORDER_TYPE_BUY
    SELL = mt5.ORDER_TYPE_SELL
    BUY_LIMIT = mt5.ORDER_TYPE_BUY_LIMIT
    SELL_LIMIT = mt5.ORDER_TYPE_SELL_LIMIT
    BUY_STOP = mt5.ORDER_TYPE_BUY_STOP
    SELL_STOP = mt5.ORDER_TYPE_SELL_STOP


class MT5Executor:
    """
    Executes and manages trades on MetaTrader 5.
    Production-ready with complete error handling.
    """
    
    def __init__(self, config, connector: MT5Connector):
        """
        Initialize MT5 executor.
        
        Args:
            config: Settings object
            connector: MT5Connector instance
        """
        self.config = config
        self.connector = connector
        self.logger = get_logger(__name__, config.LOG_LEVEL, config.LOG_FILE_PATH)
        self.magic_number = config.MT5_MAGIC_NUMBER
    
    def open_position(
        self,
        symbol: str,
        order_type: str,
        lot_size: float,
        stop_loss: float,
        take_profit: float,
        comment: str = "NYX Bot"
    ) -> Optional[Dict]:
        """
        Open a new trading position.
        
        Args:
            symbol: Trading symbol
            order_type: 'BUY' or 'SELL'
            lot_size: Position size in lots
            stop_loss: Stop loss price
            take_profit: Take profit price
            comment: Order comment
            
        Returns:
            Dictionary with order result or None
        """
        if not self.connector.connected:
            self.logger.error("Not connected to MT5")
            return None
        
        if not self.config.AUTO_TRADING_ENABLED:
            self.logger.warning("Auto trading is disabled. Order not executed.")
            self.logger.info(f"SIGNAL: {order_type} {symbol} @ {lot_size} lots, SL: {stop_loss}, TP: {take_profit}")
            return None
        
        try:
            # Get symbol info
            symbol_info = self.connector.get_symbol_info(symbol)
            if symbol_info is None:
                self.logger.error(f"Failed to get symbol info for {symbol}")
                return None
            
            # Get current price
            price_info = self.connector.get_current_price(symbol)
            if price_info is None:
                self.logger.error(f"Failed to get current price for {symbol}")
                return None
            
            # Determine order type and price
            if order_type.upper() == "BUY":
                mt5_order_type = mt5.ORDER_TYPE_BUY
                price = price_info['ask']
            elif order_type.upper() == "SELL":
                mt5_order_type = mt5.ORDER_TYPE_SELL
                price = price_info['bid']
            else:
                self.logger.error(f"Invalid order type: {order_type}")
                return None
            
            # Normalize prices to symbol digits
            digits = symbol_info['digits']
            price = round(price, digits)
            stop_loss = round(stop_loss, digits)
            take_profit = round(take_profit, digits)
            
            # Prepare order request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": float(lot_size),
                "type": mt5_order_type,
                "price": price,
                "sl": stop_loss,
                "tp": take_profit,
                "deviation": self.config.MT5_DEVIATION,
                "magic": self.magic_number,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": self._get_filling_mode()
            }
            
            # Send order
            result = mt5.order_send(request)
            
            if result is None:
                self.logger.error(f"Order send failed: {mt5.last_error()}")
                return None
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Order failed with retcode: {result.retcode}")
                self.logger.error(f"Error description: {self._get_error_description(result.retcode)}")
                return None
            
            # Order successful
            order_result = {
                'ticket': result.order,
                'symbol': symbol,
                'type': order_type,
                'volume': lot_size,
                'price': result.price,
                'sl': stop_loss,
                'tp': take_profit,
                'time': datetime.now(),
                'comment': comment
            }
            
            self.logger.info(f"Position opened: {order_type} {symbol} @ {result.price}, Ticket: {result.order}")
            self.logger.trade_execution(
                "OPENED",
                symbol,
                {
                    'price': result.price,
                    'quantity': lot_size,
                    'ticket': result.order
                }
            )
            
            return order_result
            
        except Exception as e:
            self.logger.exception(f"Error opening position: {e}")
            return None
    
    def close_position(
        self,
        ticket: int,
        partial_close: bool = False,
        close_percent: float = 100.0
    ) -> bool:
        """
        Close an existing position.
        
        Args:
            ticket: Position ticket number
            partial_close: Whether to partially close
            close_percent: Percentage to close (if partial)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connector.connected:
            self.logger.error("Not connected to MT5")
            return False
        
        if not self.config.AUTO_TRADING_ENABLED:
            self.logger.warning("Auto trading is disabled. Position not closed.")
            return False
        
        try:
            # Get position info
            position = mt5.positions_get(ticket=ticket)
            
            if position is None or len(position) == 0:
                self.logger.error(f"Position {ticket} not found")
                return False
            
            position = position[0]
            
            # Calculate volume to close
            if partial_close:
                volume = position.volume * (close_percent / 100.0)
                volume = round(volume, 2)
            else:
                volume = position.volume
            
            # Determine closing order type
            if position.type == mt5.ORDER_TYPE_BUY:
                close_type = mt5.ORDER_TYPE_SELL
                price = mt5.symbol_info_tick(position.symbol).bid
            else:
                close_type = mt5.ORDER_TYPE_BUY
                price = mt5.symbol_info_tick(position.symbol).ask
            
            # Prepare close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": float(volume),
                "type": close_type,
                "position": ticket,
                "price": price,
                "deviation": self.config.MT5_DEVIATION,
                "magic": self.magic_number,
                "comment": "Close by NYX Bot",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": self._get_filling_mode()
            }
            
            # Send close order
            result = mt5.order_send(request)
            
            if result is None:
                self.logger.error(f"Close order failed: {mt5.last_error()}")
                return False
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Close failed with retcode: {result.retcode}")
                return False
            
            # Calculate P&L
            pnl = result.profit if hasattr(result, 'profit') else 0.0
            
            self.logger.info(f"Position closed: Ticket {ticket}, P&L: {pnl}")
            self.logger.trade_execution(
                "CLOSED" if not partial_close else "PARTIAL_CLOSE",
                position.symbol,
                {
                    'price': price,
                    'quantity': volume,
                    'pnl': pnl
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Error closing position: {e}")
            return False
    
    def modify_position(
        self,
        ticket: int,
        new_sl: Optional[float] = None,
        new_tp: Optional[float] = None
    ) -> bool:
        """
        Modify stop loss and/or take profit of an existing position.
        
        Args:
            ticket: Position ticket number
            new_sl: New stop loss price (optional)
            new_tp: New take profit price (optional)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connector.connected:
            self.logger.error("Not connected to MT5")
            return False
        
        try:
            # Get position info
            position = mt5.positions_get(ticket=ticket)
            
            if position is None or len(position) == 0:
                self.logger.error(f"Position {ticket} not found")
                return False
            
            position = position[0]
            
            # Use existing values if not provided
            sl = new_sl if new_sl is not None else position.sl
            tp = new_tp if new_tp is not None else position.tp
            
            # Get symbol info for digits
            symbol_info = self.connector.get_symbol_info(position.symbol)
            if symbol_info is None:
                return False
            
            digits = symbol_info['digits']
            sl = round(sl, digits)
            tp = round(tp, digits)
            
            # Prepare modification request
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "position": ticket,
                "sl": sl,
                "tp": tp
            }
            
            # Send modification
            result = mt5.order_send(request)
            
            if result is None:
                self.logger.error(f"Modify order failed: {mt5.last_error()}")
                return False
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Modify failed with retcode: {result.retcode}")
                return False
            
            self.logger.info(f"Position modified: Ticket {ticket}, SL: {sl}, TP: {tp}")
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Error modifying position: {e}")
            return False
    
    def get_open_positions(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get all open positions.
        
        Args:
            symbol: Filter by symbol (optional)
            
        Returns:
            List of position dictionaries
        """
        if not self.connector.connected:
            self.logger.error("Not connected to MT5")
            return []
        
        try:
            if symbol:
                positions = mt5.positions_get(symbol=symbol)
            else:
                positions = mt5.positions_get()
            
            if positions is None:
                return []
            
            position_list = []
            for pos in positions:
                position_list.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL',
                    'volume': pos.volume,
                    'price_open': pos.price_open,
                    'price_current': pos.price_current,
                    'sl': pos.sl,
                    'tp': pos.tp,
                    'profit': pos.profit,
                    'swap': pos.swap,
                    'comment': pos.comment,
                    'time': datetime.fromtimestamp(pos.time)
                })
            
            return position_list
            
        except Exception as e:
            self.logger.exception(f"Error getting positions: {e}")
            return []
    
    def get_position_count(self) -> int:
        """
        Get number of open positions.
        
        Returns:
            Number of open positions
        """
        positions = self.get_open_positions()
        return len(positions)
    
    def close_all_positions(self, symbol: Optional[str] = None) -> int:
        """
        Close all open positions.
        
        Args:
            symbol: Close only positions for this symbol (optional)
            
        Returns:
            Number of positions closed
        """
        positions = self.get_open_positions(symbol)
        closed_count = 0
        
        for pos in positions:
            if self.close_position(pos['ticket']):
                closed_count += 1
        
        self.logger.info(f"Closed {closed_count} positions")
        return closed_count
    
    def get_daily_profit(self) -> float:
        """
        Calculate today's profit/loss.
        
        Returns:
            Total P&L for today
        """
        if not self.connector.connected:
            return 0.0
        
        try:
            # Get today's deals
            from datetime import date
            today = date.today()
            
            deals = mt5.history_deals_get(
                date(today.year, today.month, today.day),
                datetime.now()
            )
            
            if deals is None:
                return 0.0
            
            total_profit = sum(deal.profit for deal in deals if deal.magic == self.magic_number)
            
            return total_profit
            
        except Exception as e:
            self.logger.exception(f"Error calculating daily profit: {e}")
            return 0.0
    
    def check_daily_loss_limit(self) -> bool:
        """
        Check if daily loss limit has been reached.
        
        Returns:
            True if limit reached, False otherwise
        """
        account = self.connector.get_account_info()
        if account is None:
            return True
        
        daily_profit = self.get_daily_profit()
        max_loss = account['balance'] * (self.config.MAX_DAILY_LOSS_PERCENT / 100)
        
        if daily_profit < -max_loss:
            self.logger.warning(f"Daily loss limit reached: {daily_profit}")
            return True
        
        return False
    
    def place_pending_order(
        self,
        symbol: str,
        order_type: str,
        lot_size: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        comment: str = "NYX Bot Pending"
    ) -> Optional[Dict]:
        """
        Place a pending order (Buy Stop, Sell Stop, Buy Limit, Sell Limit).
        
        Args:
            symbol: Trading symbol
            order_type: 'BUY_STOP', 'SELL_STOP', 'BUY_LIMIT', 'SELL_LIMIT'
            lot_size: Position size in lots
            entry_price: Price to enter trade
            stop_loss: Stop loss price
            take_profit: Take profit price
            comment: Order comment
            
        Returns:
            Dictionary with order result or None
        """
        if not self.connector.connected:
            self.logger.error("Not connected to MT5")
            return None
        
        if not self.config.AUTO_TRADING_ENABLED:
            self.logger.warning("Auto trading is disabled. Pending order not placed.")
            self.logger.info(
                f"PENDING SIGNAL: {order_type} {symbol} @ {entry_price}, "
                f"Size: {lot_size} lots, SL: {stop_loss}, TP: {take_profit}"
            )
            return None
        
        try:
            # Get symbol info
            symbol_info = self.connector.get_symbol_info(symbol)
            if symbol_info is None:
                self.logger.error(f"Failed to get symbol info for {symbol}")
                return None
            
            # Determine MT5 order type
            order_type_map = {
                'BUY_STOP': mt5.ORDER_TYPE_BUY_STOP,
                'SELL_STOP': mt5.ORDER_TYPE_SELL_STOP,
                'BUY_LIMIT': mt5.ORDER_TYPE_BUY_LIMIT,
                'SELL_LIMIT': mt5.ORDER_TYPE_SELL_LIMIT
            }
            
            mt5_order_type = order_type_map.get(order_type)
            if mt5_order_type is None:
                self.logger.error(f"Invalid pending order type: {order_type}")
                return None
            
            # Normalize prices to symbol digits
            digits = symbol_info['digits']
            entry_price = round(entry_price, digits)
            stop_loss = round(stop_loss, digits)
            take_profit = round(take_profit, digits)
            
            # Prepare order request
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": float(lot_size),
                "type": mt5_order_type,
                "price": entry_price,
                "sl": stop_loss,
                "tp": take_profit,
                "deviation": self.config.MT5_DEVIATION,
                "magic": self.magic_number,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": self._get_filling_mode()
            }
            
            # Send order
            result = mt5.order_send(request)
            
            if result is None:
                self.logger.error(f"Pending order failed: {mt5.last_error()}")
                return None
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Pending order failed with retcode: {result.retcode}")
                self.logger.error(f"Error: {self._get_error_description(result.retcode)}")
                return None
            
            # Order successful
            order_result = {
                'order': result.order,
                'symbol': symbol,
                'type': order_type,
                'volume': lot_size,
                'entry_price': entry_price,
                'sl': stop_loss,
                'tp': take_profit,
                'time': datetime.now(),
                'comment': comment
            }
            
            self.logger.info(
                f"Pending order placed: {order_type} {symbol} @ {entry_price}, "
                f"Order: {result.order}"
            )
            
            return order_result
            
        except Exception as e:
            self.logger.exception(f"Error placing pending order: {e}")
            return None
    
    def manage_tp1_hit(
        self,
        ticket: int,
        entry_price: float
    ) -> bool:
        """
        Manage position when TP1 is hit:
        1. Close 50% of position
        2. Move SL to breakeven (entry price)
        
        Args:
            ticket: Position ticket number
            entry_price: Original entry price
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connector.connected:
            self.logger.error("Not connected to MT5")
            return False
        
        if not self.config.AUTO_TRADING_ENABLED:
            self.logger.info("Auto trading disabled - TP1 management skipped")
            return False
        
        try:
            self.logger.info(f"Managing TP1 hit for ticket {ticket}")
            
            # Step 1: Close 50% of position
            close_percent = self.config.PARTIAL_CLOSE_TP1_PERCENT
            
            if self.close_position(ticket, partial_close=True, close_percent=close_percent):
                self.logger.info(f"Closed {close_percent}% at TP1")
            else:
                self.logger.error("Failed to partial close at TP1")
                return False
            
            # Step 2: Move SL to breakeven if enabled
            if self.config.MOVE_SL_TO_BREAKEVEN_AT_TP1:
                # Small buffer above/below entry to account for spread
                buffer_pips = 2  # 2 pip buffer
                
                # Get position info
                position = mt5.positions_get(ticket=ticket)
                
                if position is None or len(position) == 0:
                    self.logger.warning(f"Position {ticket} not found (may be fully closed)")
                    return True  # Not an error if position is closed
                
                position = position[0]
                
                # Get symbol info for pip calculation
                symbol_info = self.connector.get_symbol_info(position.symbol)
                if not symbol_info:
                    return False
                
                # Calculate buffer based on pip value
                if 'JPY' in position.symbol:
                    buffer = buffer_pips * 0.01
                else:
                    buffer = buffer_pips * 0.0001
                
                # Set new SL at breakeven with buffer
                if position.type == mt5.ORDER_TYPE_BUY:
                    new_sl = entry_price + buffer
                else:
                    new_sl = entry_price - buffer
                
                # Modify position SL
                if self.modify_position(ticket, new_sl=new_sl):
                    self.logger.info(f"Moved SL to breakeven: {new_sl:.5f}")
                else:
                    self.logger.error("Failed to move SL to breakeven")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Error managing TP1: {e}")
            return False
    
    def _get_filling_mode(self) -> int:
        """
        Get order filling mode based on configuration.
        
        Returns:
            MT5 filling mode constant
        """
        filling_modes = {
            "FOK": mt5.ORDER_FILLING_FOK,
            "IOC": mt5.ORDER_FILLING_IOC,
            "RETURN": mt5.ORDER_FILLING_RETURN
        }
        
        return filling_modes.get(
            self.config.MT5_FILLING_MODE,
            mt5.ORDER_FILLING_FOK
        )
    
    def _get_error_description(self, retcode: int) -> str:
        """
        Get human-readable error description.
        
        Args:
            retcode: MT5 return code
            
        Returns:
            Error description string
        """
        error_descriptions = {
            mt5.TRADE_RETCODE_REQUOTE: "Requote",
            mt5.TRADE_RETCODE_REJECT: "Request rejected",
            mt5.TRADE_RETCODE_CANCEL: "Request canceled",
            mt5.TRADE_RETCODE_PLACED: "Order placed",
            mt5.TRADE_RETCODE_DONE: "Request completed",
            mt5.TRADE_RETCODE_DONE_PARTIAL: "Partial execution",
            mt5.TRADE_RETCODE_ERROR: "Request error",
            mt5.TRADE_RETCODE_TIMEOUT: "Request timeout",
            mt5.TRADE_RETCODE_INVALID: "Invalid request",
            mt5.TRADE_RETCODE_INVALID_VOLUME: "Invalid volume",
            mt5.TRADE_RETCODE_INVALID_PRICE: "Invalid price",
            mt5.TRADE_RETCODE_INVALID_STOPS: "Invalid stops",
            mt5.TRADE_RETCODE_TRADE_DISABLED: "Trade disabled",
            mt5.TRADE_RETCODE_MARKET_CLOSED: "Market closed",
            mt5.TRADE_RETCODE_NO_MONEY: "Not enough money",
            mt5.TRADE_RETCODE_PRICE_CHANGED: "Price changed",
            mt5.TRADE_RETCODE_PRICE_OFF: "No prices",
            mt5.TRADE_RETCODE_INVALID_EXPIRATION: "Invalid expiration",
            mt5.TRADE_RETCODE_ORDER_CHANGED: "Order changed",
            mt5.TRADE_RETCODE_TOO_MANY_REQUESTS: "Too many requests",
            mt5.TRADE_RETCODE_NO_CHANGES: "No changes",
            mt5.TRADE_RETCODE_SERVER_DISABLES_AT: "Autotrading disabled by server",
            mt5.TRADE_RETCODE_CLIENT_DISABLES_AT: "Autotrading disabled by client",
            mt5.TRADE_RETCODE_LOCKED: "Request locked",
            mt5.TRADE_RETCODE_FROZEN: "Order or position frozen",
            mt5.TRADE_RETCODE_INVALID_FILL: "Invalid order filling type",
        }
        
        return error_descriptions.get(retcode, f"Unknown error code: {retcode}")


if __name__ == "__main__":
    # Test trade executor
    from config.settings import settings
    
    print("Testing MT5 Executor...")
    print("NOTE: AUTO_TRADING_ENABLED must be false for testing")
    
    connector = MT5Connector(settings)
    
    if connector.connect():
        executor = MT5Executor(settings, connector)
        
        # Test getting positions
        positions = executor.get_open_positions()
        print(f"\nOpen positions: {len(positions)}")
        
        for pos in positions:
            print(f"  {pos['type']} {pos['symbol']} @ {pos['price_open']}, P&L: {pos['profit']}")
        
        # Test daily profit
        daily_pnl = executor.get_daily_profit()
        print(f"\nDaily P&L: {daily_pnl}")
        
        connector.disconnect()
    else:
        print("\nConnection failed!")