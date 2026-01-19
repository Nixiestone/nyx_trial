"""
Strategy Tests
Author: BLESSING OMOREGIE
"""

import pytest
import numpy as np
import pandas as pd
from src.strategy.structure import MarketStructureDetector
from src.strategy.poi_detector import POIDetector
from src.strategy.smc_analysis import SMCAnalyzer


def create_sample_data(length=500):
    """Create sample OHLCV data."""
    dates = pd.date_range('2023-01-01', periods=length, freq='1H')
    return pd.DataFrame({
        'open': np.random.uniform(100, 110, length),
        'high': np.random.uniform(110, 115, length),
        'low': np.random.uniform(95, 100, length),
        'close': np.random.uniform(100, 110, length),
        'volume': np.random.uniform(1000, 2000, length)
    }, index=dates)


def test_market_structure_detector():
    """Test market structure detection."""
    df = create_sample_data()
    detector = MarketStructureDetector()
    
    analysis = detector.analyze_market_structure(df)
    
    assert analysis is not None
    assert 'trend' in analysis
    assert 'swing_highs' in analysis
    assert 'swing_lows' in analysis


def test_poi_detector():
    """Test POI detection."""
    df = create_sample_data()
    detector = POIDetector()
    
    obs = detector.detect_order_blocks(df, direction="bullish")
    fvgs = detector.detect_fair_value_gaps(df, direction="bullish")
    
    assert isinstance(obs, list)
    assert isinstance(fvgs, list)


def test_smc_analyzer():
    """Test SMC analysis."""
    df = create_sample_data()
    analyzer = SMCAnalyzer()
    
    htf_context = analyzer.analyze_htf_context(df)
    
    assert htf_context is not None
    assert 'trend' in htf_context


if __name__ == "__main__":
    pytest.main([__file__, "-v"])