"""
Point of Interest (POI) Detection Module
Author: BLESSING OMOREGIE 

"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class POIType(Enum):
    """Type of Point of Interest."""
    ORDER_BLOCK = "OB"
    BREAKER_BLOCK = "BB"
    FAIR_VALUE_GAP = "FVG"


@dataclass
class PointOfInterest:
    """Represents a Point of Interest in the market."""
    poi_type: POIType
    price_high: float
    price_low: float
    candle_index: int
    body_high: float
    body_low: float
    triggered_structure: bool
    has_inducement: bool
    is_unmitigated: bool
    distance_to_liquidity: float
    direction: str
    fvg_overlap: bool = False
    timestamp: Optional[pd.Timestamp] = None
    
    def is_valid(self) -> bool:
        """Check if POI meets all 4 rules for selection."""
        return (
            self.triggered_structure and
            self.has_inducement and
            self.is_unmitigated and
            self.distance_to_liquidity >= 0
        )
    
    def get_entry_price(self, entry_type: str = "standard") -> float:
        """Calculate entry price based on entry type."""
        if entry_type == "breaker" and self.poi_type == POIType.BREAKER_BLOCK:
            return (self.body_high + self.body_low) / 2
        else:
            return (self.body_high + self.body_low) / 2


class POIDetector:
    """
    FIXED: Proper POI detection with 200-candle lookback on LTF
    
    CRITICAL CHANGES:
    - LTF lookback: 200 candles (for M5/M15)
    - ITF lookback: 150 candles (for H1)
    - HTF lookback: 100 candles (for H4/D1)
    """
    
    def __init__(self, timeframe: str = "M15"):
        """
        Initialize POI detector with CORRECT lookback windows.
        
        Args:
            timeframe: Trading timeframe
        """
        self.timeframe = timeframe
        
        # FIXED: Proper lookback based on timeframe
        if timeframe in ["M5", "M1"]:
            self.primary_lookback = 200  # LTF: 200 candles
            self.max_poi_distance = 50
        elif timeframe in ["M15", "M30"]:
            self.primary_lookback = 200  # LTF: 200 candles  
            self.max_poi_distance = 60
        elif timeframe == "H1":
            self.primary_lookback = 150  # ITF: 150 candles
            self.max_poi_distance = 40
        elif timeframe in ["H4", "D1"]:
            self.primary_lookback = 100  # HTF: 100 candles
            self.max_poi_distance = 30
        else:
            self.primary_lookback = 200
            self.max_poi_distance = 50
        
        self.fvg_min_size_percent = 0.1
    
    def detect_order_blocks(
        self,
        df: pd.DataFrame,
        direction: str = "bullish",
        inducement_index: Optional[int] = None,
        structure_break_index: Optional[int] = None
    ) -> List[PointOfInterest]:
        """
        Detect Order Blocks with CORRECT 200-candle lookback.
        
        FIXED: Now properly scans last 200 candles on LTF
        """
        order_blocks = []
        
        # Use structure_break_index if provided, else use end of data
        if structure_break_index is not None:
            scan_end = structure_break_index
        else:
            scan_end = len(df) - 1
        
        if inducement_index is None:
            inducement_index = scan_end
        
        # CRITICAL FIX: Proper lookback window
        start_index = max(0, scan_end - self.primary_lookback)
        
        # Log for verification
        candles_scanned = scan_end - start_index
        
        for i in range(start_index, scan_end):
            is_bullish_candle = df['close'].iloc[i] > df['open'].iloc[i]
            is_bearish_candle = df['close'].iloc[i] < df['open'].iloc[i]
            
            # For bullish OB: last bearish candle before displacement
            if direction == "bullish" and is_bearish_candle:
                if i + 3 < len(df):
                    next_candles = df.iloc[i+1:min(i+4, len(df))]
                    bullish_displacement = (next_candles['close'] > next_candles['open']).sum() >= 2
                    
                    displacement_range = next_candles['high'].max() - next_candles['low'].min()
                    avg_range = df['high'].iloc[max(0, i-5):i].sub(df['low'].iloc[max(0, i-5):i]).mean() if i >= 5 else displacement_range
                    
                    if bullish_displacement and displacement_range > avg_range * 1.5:
                        ob = PointOfInterest(
                            poi_type=POIType.ORDER_BLOCK,
                            price_high=df['high'].iloc[i],
                            price_low=df['low'].iloc[i],
                            candle_index=i,
                            body_high=max(df['open'].iloc[i], df['close'].iloc[i]),
                            body_low=min(df['open'].iloc[i], df['close'].iloc[i]),
                            triggered_structure=True,
                            has_inducement=False,
                            is_unmitigated=self._check_mitigation_50_percent(df, i, inducement_index, direction),
                            distance_to_liquidity=self._calculate_distance_to_inducement(i, inducement_index),
                            direction=direction,
                            timestamp=df.index[i] if hasattr(df.index, 'to_timestamp') else None
                        )
                        
                        candle_distance = inducement_index - i
                        if candle_distance <= self.max_poi_distance:
                            order_blocks.append(ob)
            
            # For bearish OB: last bullish candle before displacement
            elif direction == "bearish" and is_bullish_candle:
                if i + 3 < len(df):
                    next_candles = df.iloc[i+1:min(i+4, len(df))]
                    bearish_displacement = (next_candles['close'] < next_candles['open']).sum() >= 2
                    
                    displacement_range = next_candles['high'].max() - next_candles['low'].min()
                    avg_range = df['high'].iloc[max(0, i-5):i].sub(df['low'].iloc[max(0, i-5):i]).mean() if i >= 5 else displacement_range
                    
                    if bearish_displacement and displacement_range > avg_range * 1.5:
                        ob = PointOfInterest(
                            poi_type=POIType.ORDER_BLOCK,
                            price_high=df['high'].iloc[i],
                            price_low=df['low'].iloc[i],
                            candle_index=i,
                            body_high=max(df['open'].iloc[i], df['close'].iloc[i]),
                            body_low=min(df['open'].iloc[i], df['close'].iloc[i]),
                            triggered_structure=True,
                            has_inducement=False,
                            is_unmitigated=self._check_mitigation_50_percent(df, i, inducement_index, direction),
                            distance_to_liquidity=self._calculate_distance_to_inducement(i, inducement_index),
                            direction=direction,
                            timestamp=df.index[i] if hasattr(df.index, 'to_timestamp') else None
                        )
                        
                        candle_distance = inducement_index - i
                        if candle_distance <= self.max_poi_distance:
                            order_blocks.append(ob)
        
        # Sort by proximity
        order_blocks.sort(key=lambda x: x.distance_to_liquidity)
        
        return order_blocks
    
    def detect_breaker_blocks(
        self,
        df: pd.DataFrame,
        direction: str = "bullish",
        inducement_index: Optional[int] = None,
        structure_break_index: Optional[int] = None
    ) -> List[PointOfInterest]:
        """
        Detect Breaker Blocks with CORRECT 200-candle lookback.
        """
        breaker_blocks = []
        
        if structure_break_index is not None:
            scan_end = structure_break_index
        else:
            scan_end = len(df) - 1
        
        if inducement_index is None:
            inducement_index = scan_end
        
        # CRITICAL FIX: Proper lookback
        start_index = max(0, scan_end - self.primary_lookback)
        
        for i in range(start_index, scan_end):
            candle_high = df['high'].iloc[i]
            candle_low = df['low'].iloc[i]
            body_high = max(df['open'].iloc[i], df['close'].iloc[i])
            body_low = min(df['open'].iloc[i], df['close'].iloc[i])
            
            if i + 3 < len(df):
                if direction == "bullish":
                    broke_below = df['low'].iloc[i+1] < candle_low
                    displacement_candles = df.iloc[i+1:min(i+4, len(df))]
                    has_displacement = (displacement_candles['close'] < displacement_candles['open']).sum() >= 2
                    body_unmitigated = self._is_body_unmitigated(df, i, direction)
                    
                    if broke_below and has_displacement and body_unmitigated:
                        bb = PointOfInterest(
                            poi_type=POIType.BREAKER_BLOCK,
                            price_high=candle_high,
                            price_low=candle_low,
                            candle_index=i,
                            body_high=body_high,
                            body_low=body_low,
                            triggered_structure=True,
                            has_inducement=False,
                            is_unmitigated=body_unmitigated,
                            distance_to_liquidity=self._calculate_distance_to_inducement(i, inducement_index),
                            direction=direction,
                            timestamp=df.index[i] if hasattr(df.index, 'to_timestamp') else None
                        )
                        
                        candle_distance = inducement_index - i
                        if candle_distance <= self.max_poi_distance:
                            breaker_blocks.append(bb)
                
                elif direction == "bearish":
                    broke_above = df['high'].iloc[i+1] > candle_high
                    displacement_candles = df.iloc[i+1:min(i+4, len(df))]
                    has_displacement = (displacement_candles['close'] > displacement_candles['open']).sum() >= 2
                    body_unmitigated = self._is_body_unmitigated(df, i, direction)
                    
                    if broke_above and has_displacement and body_unmitigated:
                        bb = PointOfInterest(
                            poi_type=POIType.BREAKER_BLOCK,
                            price_high=candle_high,
                            price_low=candle_low,
                            candle_index=i,
                            body_high=body_high,
                            body_low=body_low,
                            triggered_structure=True,
                            has_inducement=False,
                            is_unmitigated=body_unmitigated,
                            distance_to_liquidity=self._calculate_distance_to_inducement(i, inducement_index),
                            direction=direction,
                            timestamp=df.index[i] if hasattr(df.index, 'to_timestamp') else None
                        )
                        
                        candle_distance = inducement_index - i
                        if candle_distance <= self.max_poi_distance:
                            breaker_blocks.append(bb)
        
        breaker_blocks.sort(key=lambda x: x.distance_to_liquidity)
        return breaker_blocks
    
    # Helper methods remain the same...
    def _check_mitigation_50_percent(self, df, poi_index, inducement_index, direction) -> bool:
        """50% mean threshold mitigation check."""
        if poi_index >= inducement_index:
            return True
        
        poi_high = df['high'].iloc[poi_index]
        poi_low = df['low'].iloc[poi_index]
        mean_threshold = (poi_high + poi_low) / 2
        
        for i in range(poi_index + 1, inducement_index + 1):
            candle_high = df['high'].iloc[i]
            candle_low = df['low'].iloc[i]
            
            if direction == "bullish":
                if candle_low <= mean_threshold:
                    return False
            elif direction == "bearish":
                if candle_high >= mean_threshold:
                    return False
        
        return True
    
    def _calculate_distance_to_inducement(self, poi_index, inducement_index) -> float:
        """Calculate candle distance from POI to Inducement."""
        return float(inducement_index - poi_index)
    
    def _is_body_unmitigated(self, df, candle_index, direction) -> bool:
        """Check if POI body is unmitigated (for Breaker Blocks)."""
        if candle_index >= len(df) - 1:
            return True
        
        body_high = max(df['open'].iloc[candle_index], df['close'].iloc[candle_index])
        body_low = min(df['open'].iloc[candle_index], df['close'].iloc[candle_index])
        
        for i in range(candle_index + 1, len(df)):
            if direction == "bullish":
                if df['low'].iloc[i] <= body_low:
                    return False
            elif direction == "bearish":
                if df['high'].iloc[i] >= body_high:
                    return False
        
        return True
    
    def detect_fair_value_gaps(self, df, direction) -> List[PointOfInterest]:
        """Detect FVGs (unchanged - already correct)."""
        fvgs = []
        
        for i in range(2, len(df)):
            if direction == "bullish":
                gap_bottom = df['high'].iloc[i-2]
                gap_top = df['low'].iloc[i]
                
                if gap_top > gap_bottom:
                    gap_size = gap_top - gap_bottom
                    gap_percent = (gap_size / gap_bottom) * 100
                    
                    if gap_percent >= self.fvg_min_size_percent:
                        fvg = PointOfInterest(
                            poi_type=POIType.FAIR_VALUE_GAP,
                            price_high=gap_top,
                            price_low=gap_bottom,
                            candle_index=i-1,
                            body_high=gap_top,
                            body_low=gap_bottom,
                            triggered_structure=True,
                            has_inducement=False,
                            is_unmitigated=self._is_fvg_unmitigated(df, i, gap_bottom, gap_top),
                            distance_to_liquidity=0.0,
                            direction=direction,
                            fvg_overlap=False,
                            timestamp=df.index[i-1] if hasattr(df.index, 'to_timestamp') else None
                        )
                        fvgs.append(fvg)
            
            elif direction == "bearish":
                gap_top = df['low'].iloc[i-2]
                gap_bottom = df['high'].iloc[i]
                
                if gap_top > gap_bottom:
                    gap_size = gap_top - gap_bottom
                    gap_percent = (gap_size / gap_top) * 100
                    
                    if gap_percent >= self.fvg_min_size_percent:
                        fvg = PointOfInterest(
                            poi_type=POIType.FAIR_VALUE_GAP,
                            price_high=gap_top,
                            price_low=gap_bottom,
                            candle_index=i-1,
                            body_high=gap_top,
                            body_low=gap_bottom,
                            triggered_structure=True,
                            has_inducement=False,
                            is_unmitigated=self._is_fvg_unmitigated(df, i, gap_bottom, gap_top),
                            distance_to_liquidity=0.0,
                            direction=direction,
                            fvg_overlap=False,
                            timestamp=df.index[i-1] if hasattr(df.index, 'to_timestamp') else None
                        )
                        fvgs.append(fvg)
        
        return fvgs
    
    def _is_fvg_unmitigated(self, df, candle_index, gap_low, gap_high) -> bool:
        """Check if FVG is unmitigated."""
        if candle_index >= len(df) - 1:
            return True
        
        for i in range(candle_index + 1, len(df)):
            if df['low'].iloc[i] <= gap_low or df['high'].iloc[i] >= gap_high:
                return False
        
        return True


if __name__ == "__main__":
    print("POI Detector - FIXED VERSION")
    print("Lookback windows:")
    print("  M5/M15 (LTF): 200 candles")
    print("  H1 (ITF): 150 candles")
    print("  H4/D1 (HTF): 100 candles")