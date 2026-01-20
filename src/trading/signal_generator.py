"""
FIXED: Signal Generator with Correct Imports
Location: src/trading/signal_generator.py (REPLACE ENTIRE FILE)

Author: BLESSING OMOREGIE (Fixed by QDev Team)
"""

from typing import Optional, Dict
import pandas as pd
from ..strategy.smc_analysis import SMCAnalyzer
from ..models.ml_ensemble import MLEnsemble
from ..sentiment.analyzer import SentimentAnalyzer
from ..data.news_scraper import NewsScraper
from ..trading.order_type import OrderTypeDetector  # FIXED: Correct import path
from ..utils.logger import get_logger
from ..utils.symbol_normalizer import SymbolNormalizer  # NEW: Symbol normalization


class SignalGenerator:
    """Generates trading signals by combining all components."""
    
    def __init__(self, config, mt5_connector):
        self.config = config
        self.connector = mt5_connector
        self.logger = get_logger(__name__, config.LOG_LEVEL, config.LOG_FILE_PATH)
        
        # Initialize all components
        self.smc_analyzer = SMCAnalyzer(
            sl_padding_pips=config.SL_PADDING_PIPS,
            tp1_rr=2.0,  # Minimum R:R only
            tp2_rr=3.0   # Minimum R:R only
        )
        
        self.ml_ensemble = MLEnsemble(config)
        self.sentiment_analyzer = SentimentAnalyzer(config)
        self.news_scraper = NewsScraper(config)
        self.order_type_detector = OrderTypeDetector(price_tolerance_pips=2.0)
        
        # Try to load pre-trained models
        try:
            self.ml_ensemble.load_all()
        except:
            self.logger.warning("No pre-trained models found")
    
    def generate_signal(self, symbol: str) -> Optional[Dict]:
        """Generate complete trading signal for a symbol."""
        
        try:
            # STEP 1: Normalize symbol
            symbol_info = SymbolNormalizer.normalize(symbol)
            normalized_symbol = symbol_info.normalized
            
            self.logger.info(f"Generating signal for {symbol} (normalized: {normalized_symbol})")
            
            # STEP 2: Fetch market data for all timeframes
            df_htf = self.connector.get_historical_data(
                symbol,  # Use original symbol for broker
                self.config.HTF_TIMEFRAME,
                500
            )
            
            df_itf = self.connector.get_historical_data(
                symbol,
                self.config.ITF_TIMEFRAME,
                500
            )
            
            df_ltf = self.connector.get_historical_data(
                symbol,
                self.config.LTF_TIMEFRAME,
                500
            )
            
            if df_htf is None or df_itf is None or df_ltf is None:
                self.logger.error(f"Failed to fetch data for {symbol}")
                return None
            
            self.logger.debug(f"Data fetched: HTF={len(df_htf)}, ITF={len(df_itf)}, LTF={len(df_ltf)}")
            
            # STEP 3: Get current price
            current_price_info = self.connector.get_current_price(symbol)
            if not current_price_info:
                self.logger.error(f"Failed to get current price for {symbol}")
                return None
            
            current_price = current_price_info['bid']
            
            # STEP 4: Get ML prediction
            ml_prediction = self.ml_ensemble.predict(df_itf)
            self.logger.debug(f"ML prediction: {ml_prediction['ensemble']}, conf={ml_prediction['confidence']:.2f}")
            
            # STEP 5: Get sentiment analysis (use normalized symbol for news)
            news_articles = self.news_scraper.fetch_symbol_news(normalized_symbol, hours_back=24)
            sentiment = self.sentiment_analyzer.analyze_symbol_sentiment(
                normalized_symbol,
                news_articles,
                time_decay_hours=24
            )
            self.logger.debug(f"Sentiment: {sentiment['label']}, score={sentiment['score']:.2f}")
            
            # STEP 6: Generate SMC setup (use normalized symbol for pip calculations)
            setup = self.smc_analyzer.generate_trading_setup(
                df_htf,
                df_itf,
                df_ltf,
                normalized_symbol,  # Use normalized symbol for pip calculations
                ml_prediction=ml_prediction,
                sentiment_score=sentiment
            )
            
            if setup is None:
                self.logger.info(f"No valid SMC setup for {symbol}")
                return None
            
            # STEP 7: Check if should take trade
            should_trade, reason = self.smc_analyzer.should_take_trade(
                setup,
                min_confidence=self.config.ML_ENSEMBLE_THRESHOLD,
                min_risk_reward=2.0  # Minimum 1:2 (NO MAXIMUM)
            )
            
            if not should_trade:
                self.logger.info(f"Setup rejected for {symbol}: {reason}")
                return None
            
            # STEP 8: Determine order type
            order_decision = self.order_type_detector.determine_order_type(
                normalized_symbol,
                setup.direction,
                setup.entry_price,
                current_price
            )
            
            self.logger.info(
                f"Order type determined: {order_decision.order_type.value} - {order_decision.reason}"
            )
            
            # STEP 9: Create signal dictionary
            signal = {
                'symbol': symbol,  # Original broker symbol
                'normalized_symbol': normalized_symbol,  # For display
                'display_name': SymbolNormalizer.get_display_name(symbol),
                'direction': setup.direction,
                'entry_price': setup.entry_price,
                'current_price': current_price,
                'stop_loss': setup.stop_loss,
                'take_profit_1': setup.take_profit_1,
                'take_profit_2': setup.take_profit_2,
                'risk_reward_tp1': setup.risk_reward_tp1,  # Can be unlimited
                'risk_reward_tp2': setup.risk_reward_tp2,  # Can be unlimited
                'confidence': setup.confidence_score,
                'scenario': setup.scenario.value,
                'poi_type': setup.poi.poi_type.value if setup.poi else None,
                'ml_prediction': ml_prediction,
                'sentiment': sentiment,
                'timestamp': setup.timestamp,
                'inducement_swept': setup.inducement_swept,
                'fvg_validation': setup.fvg_validation,
                # Order type information
                'order_type': order_decision.order_type.value,
                'order_type_enum': order_decision.order_type.name,
                'execution_price': order_decision.execution_price,
                'immediate_execution': order_decision.immediate_execution,
                'pending_order': order_decision.pending_order,
                'order_reason': order_decision.reason
            }
            
            self.logger.trade_signal(
                setup.direction,
                symbol,
                {
                    'entry': signal['entry_price'],
                    'stop_loss': signal['stop_loss'],
                    'tp1': signal['take_profit_1'],
                    'tp2': signal['take_profit_2'],
                    'score': signal['confidence'],
                    'order_type': signal['order_type']
                }
            )
            
            return signal
            
        except Exception as e:
            self.logger.exception(f"Error generating signal for {symbol}: {e}")
            return None
    
    def scan_all_symbols(self) -> Dict[str, Optional[Dict]]:
        """Scan all configured symbols for signals."""
        
        signals = {}
        
        for symbol in self.config.TRADING_SYMBOLS:
            try:
                signal = self.generate_signal(symbol)
                signals[symbol] = signal
            except Exception as e:
                self.logger.error(f"Error scanning {symbol}: {e}")
                signals[symbol] = None
        
        # Count valid signals
        valid_count = sum(1 for sig in signals.values() if sig is not None)
        self.logger.info(f"Scan complete: {valid_count}/{len(signals)} signals generated")
        
        return signals


if __name__ == "__main__":
    from config.settings import settings
    from src.data.mt5_connector import MT5Connector
    
    print("Testing Signal Generator...")
    
    connector = MT5Connector(settings)
    
    if connector.connect():
        generator = SignalGenerator(settings, connector)
        
        # Test with broker-specific symbol
        test_symbols = ["EURUSD", "XAUUSDm", "XAUUSD.a"]
        
        for sym in test_symbols:
            print(f"\nTesting symbol: {sym}")
            signal = generator.generate_signal(sym)
            
            if signal:
                print(f"  SIGNAL GENERATED!")
                print(f"  Normalized: {signal['normalized_symbol']}")
                print(f"  Display: {signal['display_name']}")
                print(f"  Direction: {signal['direction']}")
                print(f"  R:R TP1: 1:{signal['risk_reward_tp1']:.2f}")
                print(f"  R:R TP2: 1:{signal['risk_reward_tp2']:.2f}")
            else:
                print("  No signal")
        
        connector.disconnect()
    
    print("\nSignal Generator test completed!")