"""
Signal Generator - COMPLETE
Author: BLESSING OMOREGIE
GitHub: Nixiestone
Repository: nyx_trial
"""

from typing import Optional, Dict
import pandas as pd
from ..strategy.smc_analysis import SMCAnalyzer
from ..models.ml_ensemble import MLEnsemble
from ..sentiment.analyzer import SentimentAnalyzer
from ..data.news_scraper import NewsScraper
from ..utils.logger import get_logger


class SignalGenerator:
    """Generates trading signals by combining all components."""
    
    def __init__(self, config, mt5_connector):
        self.config = config
        self.connector = mt5_connector
        self.logger = get_logger(__name__, config.LOG_LEVEL, config.LOG_FILE_PATH)
        
        # Initialize all components
        self.smc_analyzer = SMCAnalyzer(
            sl_padding_pips=config.SL_PADDING_PIPS,
            tp1_rr=config.TP1_RISK_REWARD,
            tp2_rr=config.TP2_RISK_REWARD
        )
        
        self.ml_ensemble = MLEnsemble(config)
        self.sentiment_analyzer = SentimentAnalyzer(config)
        self.news_scraper = NewsScraper(config)
        
        # Try to load pre-trained models
        try:
            self.ml_ensemble.load_all()
        except:
            self.logger.warning("No pre-trained models found")
    
    def generate_signal(self, symbol: str) -> Optional[Dict]:
        """Generate complete trading signal for a symbol."""
        
        try:
            self.logger.info(f"Generating signal for {symbol}...")
            
            # Fetch market data for all timeframes
            df_htf = self.connector.get_historical_data(
                symbol,
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
            
            # Get ML prediction
            ml_prediction = self.ml_ensemble.predict(df_itf)
            self.logger.debug(f"ML prediction: {ml_prediction['ensemble']}, conf={ml_prediction['confidence']:.2f}")
            
            # Get sentiment analysis
            news_articles = self.news_scraper.fetch_symbol_news(symbol, hours_back=24)
            sentiment = self.sentiment_analyzer.analyze_symbol_sentiment(
                symbol,
                news_articles,
                time_decay_hours=24
            )
            self.logger.debug(f"Sentiment: {sentiment['label']}, score={sentiment['score']:.2f}")
            
            # Generate SMC setup
            setup = self.smc_analyzer.generate_trading_setup(
                df_htf,
                df_itf,
                df_ltf,
                ml_prediction=ml_prediction,
                sentiment_score=sentiment
            )
            
            if setup is None:
                self.logger.info(f"No valid SMC setup for {symbol}")
                return None
            
            # Check if should take trade
            should_trade, reason = self.smc_analyzer.should_take_trade(
                setup,
                min_confidence=self.config.ML_ENSEMBLE_THRESHOLD,
                min_risk_reward=self.config.TP1_RISK_REWARD
            )
            
            if not should_trade:
                self.logger.info(f"Setup rejected for {symbol}: {reason}")
                return None
            
            # Create signal dictionary
            signal = {
                'symbol': symbol,
                'direction': setup.direction,
                'entry_price': setup.entry_price,
                'stop_loss': setup.stop_loss,
                'take_profit_1': setup.take_profit_1,
                'take_profit_2': setup.take_profit_2,
                'risk_reward_tp1': setup.risk_reward_tp1,
                'risk_reward_tp2': setup.risk_reward_tp2,
                'confidence': setup.confidence_score,
                'scenario': setup.scenario.value,
                'poi_type': setup.poi.poi_type.value if setup.poi else None,
                'ml_prediction': ml_prediction,
                'sentiment': sentiment,
                'timestamp': setup.timestamp,
                'inducement_swept': setup.inducement_swept,
                'fvg_validation': setup.fvg_validation
            }
            
            self.logger.trade_signal(
                setup.direction,
                symbol,
                {
                    'entry': signal['entry_price'],
                    'stop_loss': signal['stop_loss'],
                    'tp1': signal['take_profit_1'],
                    'tp2': signal['take_profit_2'],
                    'score': signal['confidence']
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
        
        # Test single symbol
        signal = generator.generate_signal("EURUSD")
        
        if signal:
            print("\nSignal Generated:")
            print(f"  Symbol: {signal['symbol']}")
            print(f"  Direction: {signal['direction']}")
            print(f"  Entry: {signal['entry_price']}")
            print(f"  Confidence: {signal['confidence']:.2%}")
        else:
            print("\nNo signal generated")
        
        connector.disconnect()
    
    print("\nSignal Generator test completed!")