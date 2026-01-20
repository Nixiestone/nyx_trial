"""
Main Trading Bot - WITH ML SELF-TRAINING
Author: BLESSING OMOREGIE (Enhanced by QDev Team)
GitHub: Nixiestone
Repository: nyx_trial
Path: C:\Users\NIXIE\Desktop\projects\trading-bot\nyx_trial\main.py

REPLACE ENTIRE FILE
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
from src.notifications.notifier import MultiUserNotifier
from src.utils.logger import get_logger
from src.utils.symbol_normalizer import SymbolNormalizer
from src.models.ml_trainer import TrainingDataCollector, MLModelTrainer
from src.models.ml_ensemble import MLEnsemble


class TradingBot:
    """Main trading bot orchestrator with ML self-training."""
    
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
        self.data_collector = None
        self.ml_trainer = None
        self.running = False
        
        # Signal tracking for ML training
        self.active_signals = {}  # signal_id -> signal_data
    
    def initialize(self) -> bool:
        """Initialize all bot components."""
        
        try:
            # Validate configuration
            self.logger.info("Validating configuration...")
            if not validate_settings():
                self.logger.error("Configuration validation failed")
                return False
            
            # Initialize notifier first
            self.logger.info("Initializing multi-user notification system...")
            self.notifier = MultiUserNotifier(settings)
            
            # Test symbol normalizer
            self.logger.info("Testing symbol normalizer...")
            test_symbols = settings.TRADING_SYMBOLS[:3]
            for sym in test_symbols:
                norm_info = SymbolNormalizer.normalize(sym)
                self.logger.info(f"  {sym} -> {norm_info.normalized} (display: {SymbolNormalizer.get_display_name(sym)})")
            
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
            
            # Initialize ML training system
            self.logger.info("Initializing ML self-training system...")
            self.data_collector = TrainingDataCollector(settings)
            ml_ensemble = self.signal_generator.ml_ensemble  # Use same ensemble
            self.ml_trainer = MLModelTrainer(settings, ml_ensemble, self.data_collector)
            
            # Try to load existing models
            try:
                ml_ensemble.load_all()
                self.logger.info("Pre-trained ML models loaded")
            except:
                self.logger.warning("No pre-trained models found - will train from scratch")
            
            self.logger.info("All components initialized successfully")
            
            # Send startup notification
            account_info = self.connector.get_account_info()
            subscriber_count = self.notifier.get_subscriber_count()
            
            startup_details = f"""
Platform: MT5
Account: {account_info['login']}
Balance: {account_info['balance']} {account_info['currency']}
Auto Trading: {'ENABLED' if settings.AUTO_TRADING_ENABLED else 'DISABLED'}
Telegram Subscribers: {subscriber_count}
ML Training: ENABLED (auto-trains every {settings.ML_RETRAIN_INTERVAL_HOURS}h)
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
            
            # Check if ML models need retraining
            if self.ml_trainer.auto_train_if_needed():
                self.logger.info("ML models retrained successfully")
                self.notifier.send_bot_status(
                    "ML_TRAINING_COMPLETE",
                    f"Models retrained at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            
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
            
            # Update signal outcomes for ML training
            self._update_signal_outcomes()
            
        except Exception as e:
            self.logger.exception(f"Error in trading cycle: {e}")
            self.notifier.send_error_alert("Trading Cycle", str(e))
    
    def execute_trade(self, signal: dict):
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
            
            # Get current market data for ML training
            market_data = self.connector.get_historical_data(
                signal['symbol'],
                settings.ITF_TIMEFRAME,
                100
            )
            
            # Save signal for future ML training
            signal_id = self.data_collector.save_signal(signal, market_data)
            
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
                    
                    # Track signal for outcome monitoring
                    if signal_id:
                        self.active_signals[result.get('ticket')] = {
                            'signal_id': signal_id,
                            'entry_price': signal['entry_price'],
                            'stop_loss': signal['stop_loss'],
                            'direction': signal['direction']
                        }
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
    
    def _update_signal_outcomes(self):
        """Update signal outcomes for ML training based on closed positions."""
        
        try:
            # Get all positions
            positions = self.executor.get_open_positions()
            
            # Check for closed positions
            for ticket, signal_data in list(self.active_signals.items()):
                # Check if position still open
                position_open = any(p['ticket'] == ticket for p in positions)
                
                if not position_open:
                    # Position closed - determine outcome
                    signal_id = signal_data['signal_id']
                    
                    # Get trade history to determine outcome
                    # For now, use simplified logic
                    # In production, query MT5 history
                    
                    # Placeholder: determine win/loss
                    # This should be replaced with actual MT5 history query
                    outcome = 1  # 1 = win, -1 = loss, 0 = breakeven
                    pnl = 0.0  # Get actual P&L from history
                    pips = 0.0  # Calculate actual pips
                    
                    # Update database
                    self.data_collector.update_signal_outcome(
                        signal_id,
                        outcome,
                        pnl,
                        pips
                    )
                    
                    # Remove from tracking
                    del self.active_signals[ticket]
                    
                    self.logger.info(f"Updated outcome for signal {signal_id}")
        
        except Exception as e:
            self.logger.exception(f"Error updating signal outcomes: {e}")
    
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