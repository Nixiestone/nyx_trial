"""
Main Trading Bot - COMPLETE
Author: BLESSING OMOREGIE
GitHub: Nixiestone
Repository: nyx_trial
Path: C:\\Users\\NIXIE\\Desktop\\projects\\trading-bot\\nyx_trial
"""

import sys
import time
import signal
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import settings, validate_settings
from src.data.mt5_connector import MT5Connector
from src.trading.mt5_executor import MT5Executor
from src.trading.signal_generator import SignalGenerator
from src.trading.risk_manager import RiskManager
from src.notifications.notifier import Notifier
from src.utils.logger import get_logger


class TradingBot:
    """Main trading bot orchestrator."""
    
    def __init__(self):
        """Initialize the trading bot."""
        
        # Setup logger
        self.logger = get_logger("MainBot", settings.LOG_LEVEL, settings.LOG_FILE_PATH)
        
        self.logger.info("=" * 70)
        self.logger.info("NYX TRADING BOT - INITIALIZING")
        self.logger.info(f"Author: {settings.AUTHOR}")
        self.logger.info(f"GitHub: {settings.GITHUB_USERNAME}")
        self.logger.info(f"Version: {settings.APP_VERSION}")
        self.logger.info("=" * 70)
        
        # Initialize components
        self.connector = None
        self.executor = None
        self.signal_generator = None
        self.risk_manager = None
        self.notifier = None
        self.running = False
    
    def initialize(self) -> bool:
        """Initialize all bot components."""
        
        try:
            # Validate configuration
            self.logger.info("Validating configuration...")
            if not validate_settings():
                self.logger.error("Configuration validation failed")
                return False
            
            # Initialize notifier first
            self.logger.info("Initializing notification system...")
            self.notifier = Notifier(settings)
            
            # Connect to MT5
            self.logger.info("Connecting to MT5...")
            self.connector = MT5Connector(settings)
            
            if not self.connector.connect():
                self.logger.error("Failed to connect to MT5")
                self.notifier.send_error_alert("MT5 Connection", "Failed to connect to MT5")
                return False
            
            # Initialize executor
            self.logger.info("Initializing trade executor...")
            self.executor = MT5Executor(settings, self.connector)
            
            # Initialize signal generator
            self.logger.info("Initializing signal generator...")
            self.signal_generator = SignalGenerator(settings, self.connector)
            
            # Initialize risk manager
            self.logger.info("Initializing risk manager...")
            self.risk_manager = RiskManager(settings, self.connector, self.executor)
            
            self.logger.info("All components initialized successfully")
            
            # Send startup notification
            account_info = self.connector.get_account_info()
            startup_details = f"""
Platform: MT5
Account: {account_info['login']}
Balance: {account_info['balance']} {account_info['currency']}
Auto Trading: {'ENABLED' if settings.AUTO_TRADING_ENABLED else 'DISABLED'}
            """
            self.notifier.send_bot_status("STARTED", startup_details.strip())
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Initialization error: {e}")
            if self.notifier:
                self.notifier.send_error_alert("Initialization", str(e))
            return False
    
    def run_trading_cycle(self):
        """Execute one trading cycle."""
        
        try:
            self.logger.info(f"\n{'='*70}")
            self.logger.info(f"TRADING CYCLE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info(f"{'='*70}")
            
            # Check risk limits
            can_trade, reason = self.risk_manager.check_risk_limits()
            
            if not can_trade:
                self.logger.warning(f"Trading disabled: {reason}")
                self.notifier.send_error_alert("Risk Limit", reason)
                return
            
            # Scan all symbols for signals
            self.logger.info(f"Scanning {len(settings.TRADING_SYMBOLS)} symbols...")
            
            signals = self.signal_generator.scan_all_symbols()
            
            # Process each signal
            for symbol, signal in signals.items():
                if signal is None:
                    continue
                
                self.logger.info(f"Signal detected for {symbol}")
                
                # Validate trade
                is_valid, validation_reason = self.risk_manager.validate_trade(signal)
                
                if not is_valid:
                    self.logger.warning(f"Trade validation failed: {validation_reason}")
                    continue
                
                # Send signal notification
                self.notifier.send_signal_notification(signal)
                
                # Execute trade if auto-trading enabled
                if settings.AUTO_TRADING_ENABLED:
                    self.execute_trade(signal)
                else:
                    self.logger.info("Auto-trading disabled - Signal logged only")
            
            # Log risk report
            risk_report = self.risk_manager.get_risk_report()
            self.logger.info(f"\nRisk Report:")
            self.logger.info(f"  Balance: {risk_report.get('balance', 0):.2f}")
            self.logger.info(f"  Daily P&L: {risk_report.get('daily_pnl', 0):.2f}")
            self.logger.info(f"  Open Positions: {risk_report.get('open_positions', 0)}")
            
        except Exception as e:
            self.logger.exception(f"Error in trading cycle: {e}")
            self.notifier.send_error_alert("Trading Cycle", str(e))
    
    def execute_trade(self, signal: Dict):
        """Execute a trading signal (market or pending order)."""
        
        try:
            self.logger.info(f"Executing trade for {signal['symbol']}...")
            
            # Calculate position size
            lot_size = self.risk_manager.calculate_position_size(
                signal['symbol'],
                signal['entry_price'],
                signal['stop_loss']
            )
            
            # Determine if market or pending order
            immediate_execution = signal.get('immediate_execution', True)
            order_type = signal.get('order_type_enum', 'MARKET')
            
            if immediate_execution or order_type == 'MARKET':
                # Execute market order
                result = self.executor.open_position(
                    symbol=signal['symbol'],
                    order_type=signal['direction'],
                    lot_size=lot_size,
                    stop_loss=signal['stop_loss'],
                    take_profit=signal['take_profit_1'],
                    comment=f"NYX {signal['scenario']}"
                )
                
                if result:
                    self.logger.info(f"Market order executed: Ticket {result.get('ticket', 'N/A')}")
                    self.notifier.send_trade_execution("OPENED", result)
                else:
                    self.logger.error("Market order execution failed")
                    self.notifier.send_error_alert(
                        "Trade Execution",
                        f"Failed to open position for {signal['symbol']}"
                    )
            
            else:
                # Place pending order
                result = self.executor.place_pending_order(
                    symbol=signal['symbol'],
                    order_type=order_type,
                    lot_size=lot_size,
                    entry_price=signal['entry_price'],
                    stop_loss=signal['stop_loss'],
                    take_profit=signal['take_profit_1'],
                    comment=f"NYX {signal['scenario']}"
                )
                
                if result:
                    self.logger.info(f"Pending order placed: Order {result.get('order', 'N/A')}")
                    # Send notification about pending order
                    pending_details = {
                        'symbol': signal['symbol'],
                        'type': order_type,
                        'entry_price': signal['entry_price'],
                        'order': result.get('order', 'N/A')
                    }
                    self.notifier.send_pending_order_notification(pending_details)
                else:
                    self.logger.error("Pending order placement failed")
                    self.notifier.send_error_alert(
                        "Pending Order",
                        f"Failed to place pending order for {signal['symbol']}"
                    )
                
        except Exception as e:
            self.logger.exception(f"Error executing trade: {e}")
            self.notifier.send_error_alert("Trade Execution", str(e))
    
    def run(self):
        """Main bot loop."""
        
        if not self.initialize():
            self.logger.error("Bot initialization failed. Exiting.")
            return
        
        self.running = True
        self.logger.info("\nBot is now running. Press Ctrl+C to stop.\n")
        
        try:
            while self.running:
                # Run trading cycle
                self.run_trading_cycle()
                
                # Wait for next cycle
                wait_minutes = settings.MARKET_UPDATE_INTERVAL_MINUTES
                self.logger.info(f"\nWaiting {wait_minutes} minutes until next scan...\n")
                
                time.sleep(wait_minutes * 60)
                
        except KeyboardInterrupt:
            self.logger.info("\nBot stopped by user (Ctrl+C)")
        except Exception as e:
            self.logger.exception(f"Fatal error in main loop: {e}")
            self.notifier.send_error_alert("Fatal Error", str(e))
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Shutdown the bot gracefully."""
        
        self.logger.info("\nShutting down bot...")
        
        try:
            if self.notifier:
                self.notifier.send_bot_status("STOPPED")
            
            if self.connector:
                self.connector.disconnect()
            
            self.logger.info("Bot shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    print("\n\nReceived shutdown signal. Stopping bot...")
    sys.exit(0)


def main():
    """Main entry point."""
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run bot
    bot = TradingBot()
    bot.run()


if __name__ == "__main__":
    main()