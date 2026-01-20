from typing import Dict, List, Optional, Union, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
import re


class DataValidator:
    """Validates trading data and signals."""
    
    @staticmethod
    def validate_ohlcv_dataframe(df: pd.DataFrame) -> Tuple[bool, str]:
        """Validate OHLCV DataFrame structure and data quality."""
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        
        if df is None or df.empty:
            return False, "DataFrame is empty"
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return False, f"Missing required columns: {missing_columns}"
        
        if df[required_columns].isnull().any().any():
            return False, "DataFrame contains NaN values"
        
        if (df[['open', 'high', 'low', 'close', 'volume']] < 0).any().any():
            return False, "DataFrame contains negative values"
        
        if not (df['high'] >= df['low']).all():
            return False, "High prices must be >= low prices"
        
        if not ((df['high'] >= df['open']) & (df['high'] >= df['close'])).all():
            return False, "High must be the highest price"
        
        if not ((df['low'] <= df['open']) & (df['low'] <= df['close'])).all():
            return False, "Low must be the lowest price"
        
        if len(df) < 20:
            return False, "Insufficient data (minimum 20 candles required)"
        
        return True, "Valid"
    
    @staticmethod
    def validate_trading_symbol(symbol: str, platform: str = "mt5") -> Tuple[bool, str]:
        """Validate trading symbol format for MT5 or crypto exchanges."""
        if not symbol:
            return False, "Symbol is empty"
        
        symbol = symbol.strip()
        
        if platform.lower() == "mt5":
            if '/' in symbol:
                return False, "MT5 symbols don't use '/' separator (use EURUSD not EUR/USD)"
            
            if len(symbol) < 3:
                return False, "Symbol too short"
            
            if len(symbol) > 20:
                return False, "Symbol too long (max 20 characters for MT5)"
            
            if not re.match(r'^[A-Za-z0-9._-]+$', symbol):
                return False, "Symbol contains invalid characters for MT5"
            
            return True, "Valid"
        
        elif platform.lower() == "crypto":
            if '/' not in symbol:
                return False, "Crypto symbols must be in BASE/QUOTE format (e.g., BTC/USDT)"
            
            parts = symbol.split('/')
            if len(parts) != 2:
                return False, "Symbol must have exactly one '/' separator"
            
            base, quote = parts
            
            if not base or not quote:
                return False, "Base or quote currency is empty"
            
            if not base.isalnum() or not quote.isalnum():
                return False, "Symbol contains invalid characters"
            
            return True, "Valid"
        
        else:
            return False, f"Unknown platform: {platform}"
    
    @staticmethod
    def validate_timeframe(timeframe: str) -> Tuple[bool, str]:
        """Validate timeframe format."""
        valid_timeframes = [
            '1m', '3m', '5m', '15m', '30m',
            '1h', '2h', '4h', '6h', '12h',
            '1d', '3d', '1w', '1M'
        ]
        
        if timeframe not in valid_timeframes:
            return False, f"Invalid timeframe. Must be one of: {valid_timeframes}"
        
        return True, "Valid"
    
    @staticmethod
    def validate_trade_signal(signal: Dict, platform: str = "mt5") -> Tuple[bool, str]:
        """Validate trade signal structure and values."""
        required_fields = [
            'symbol', 'direction', 'entry_price',
            'stop_loss', 'take_profit_1', 'take_profit_2'
        ]
        
        missing_fields = [field for field in required_fields if field not in signal]
        if missing_fields:
            return False, f"Missing required fields: {missing_fields}"
        
        is_valid, msg = DataValidator.validate_trading_symbol(signal['symbol'], platform=platform)
        if not is_valid:
            return False, f"Invalid symbol: {msg}"
        
        if signal['direction'] not in ['BUY', 'SELL']:
            return False, "Direction must be 'BUY' or 'SELL'"
        
        price_fields = ['entry_price', 'stop_loss', 'take_profit_1', 'take_profit_2']
        for field in price_fields:
            if signal[field] <= 0:
                return False, f"{field} must be positive"
        
        if signal['direction'] == 'BUY':
            if signal['stop_loss'] >= signal['entry_price']:
                return False, "For BUY: stop_loss must be below entry_price"
            if signal['take_profit_1'] <= signal['entry_price']:
                return False, "For BUY: take_profit_1 must be above entry_price"
            if signal['take_profit_2'] <= signal['take_profit_1']:
                return False, "For BUY: take_profit_2 must be above take_profit_1"
        
        if signal['direction'] == 'SELL':
            if signal['stop_loss'] <= signal['entry_price']:
                return False, "For SELL: stop_loss must be above entry_price"
            if signal['take_profit_1'] >= signal['entry_price']:
                return False, "For SELL: take_profit_1 must be below entry_price"
            if signal['take_profit_2'] >= signal['take_profit_1']:
                return False, "For SELL: take_profit_2 must be below take_profit_1"
        
        return True, "Valid"
    
    @staticmethod
    def validate_risk_parameters(params: Dict) -> Tuple[bool, str]:
        """Validate risk management parameters."""
        required_fields = [
            'position_size_percent',
            'max_daily_loss_percent',
            'max_open_positions'
        ]
        
        missing_fields = [field for field in required_fields if field not in params]
        if missing_fields:
            return False, f"Missing required fields: {missing_fields}"
        
        if not 0 < params['position_size_percent'] <= 100:
            return False, "position_size_percent must be between 0 and 100"
        
        if params['position_size_percent'] > 10:
            return False, "position_size_percent should not exceed 10% (high risk)"
        
        if not 0 < params['max_daily_loss_percent'] <= 100:
            return False, "max_daily_loss_percent must be between 0 and 100"
        
        if not isinstance(params['max_open_positions'], int) or params['max_open_positions'] < 1:
            return False, "max_open_positions must be a positive integer"
        
        if params['max_open_positions'] > 10:
            return False, "max_open_positions should not exceed 10 (high risk)"
        
        return True, "Valid"
    
    @staticmethod
    def validate_ml_prediction(prediction: Dict) -> Tuple[bool, str]:
        """Validate machine learning prediction output."""
        required_fields = ['model1', 'model2', 'model3', 'ensemble', 'confidence']
        
        missing_fields = [field for field in required_fields if field not in prediction]
        if missing_fields:
            return False, f"Missing required fields: {missing_fields}"
        
        for model in ['model1', 'model2', 'model3', 'ensemble']:
            if prediction[model] not in [-1, 0, 1]:
                return False, f"{model} prediction must be -1 (sell), 0 (neutral), or 1 (buy)"
        
        if not 0 <= prediction['confidence'] <= 1:
            return False, "confidence must be between 0 and 1"
        
        return True, "Valid"
    
    @staticmethod
    def validate_sentiment_score(sentiment: Dict) -> Tuple[bool, str]:
        """Validate sentiment analysis output."""
        required_fields = ['score', 'label', 'confidence']
        
        missing_fields = [field for field in required_fields if field not in sentiment]
        if missing_fields:
            return False, f"Missing required fields: {missing_fields}"
        
        if not -1 <= sentiment['score'] <= 1:
            return False, "sentiment score must be between -1 and 1"
        
        if sentiment['label'] not in ['bullish', 'bearish', 'neutral']:
            return False, "label must be 'bullish', 'bearish', or 'neutral'"
        
        if not 0 <= sentiment['confidence'] <= 1:
            return False, "confidence must be between 0 and 1"
        
        return True, "Valid"
    
    @staticmethod
    def validate_poi(poi: Dict) -> Tuple[bool, str]:
        """Validate Point of Interest (POI) structure."""
        required_fields = [
            'type', 'price_high', 'price_low',
            'triggered_structure', 'has_inducement',
            'is_unmitigated', 'distance_to_liquidity'
        ]
        
        missing_fields = [field for field in required_fields if field not in poi]
        if missing_fields:
            return False, f"Missing required fields: {missing_fields}"
        
        if poi['type'] not in ['OB', 'BB', 'FVG']:
            return False, "POI type must be 'OB' (Order Block), 'BB' (Breaker Block), or 'FVG' (Fair Value Gap)"
        
        if poi['price_high'] <= poi['price_low']:
            return False, "price_high must be greater than price_low"
        
        for field in ['triggered_structure', 'has_inducement', 'is_unmitigated']:
            if not isinstance(poi[field], bool):
                return False, f"{field} must be boolean"
        
        if not poi['triggered_structure']:
            return False, "POI must trigger a shift in market structure or break of structure"
        
        if not poi['has_inducement']:
            return False, "POI must have inducement or liquidity protecting it"
        
        if not poi['is_unmitigated']:
            return False, "POI must be unmitigated"
        
        return True, "Valid"


class ConfigValidator:
    """Validates bot configuration."""
    
    @staticmethod
    def validate_api_key(api_key: str, key_name: str = "API Key") -> Tuple[bool, str]:
        """Validate API key format."""
        if not api_key:
            return False, f"{key_name} is empty"
        
        if len(api_key) < 10:
            return False, f"{key_name} is too short"
        
        placeholder_keywords = [
            'your_', 'example', 'test', 'demo', 'placeholder',
            'xxx', '123', 'abc', 'key_here'
        ]
        
        if any(keyword in api_key.lower() for keyword in placeholder_keywords):
            return False, f"{key_name} appears to be a placeholder value"
        
        return True, "Valid"
    
    @staticmethod
    def validate_telegram_chat_id(chat_id: str) -> Tuple[bool, str]:
        """Validate Telegram chat ID format."""
        if not chat_id:
            return False, "Chat ID is empty"
        
        chat_id = chat_id.strip()
        
        if not (chat_id.lstrip('-').isdigit()):
            return False, "Chat ID must be numeric"
        
        return True, "Valid"