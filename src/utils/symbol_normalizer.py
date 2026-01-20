"""
Production-Grade Symbol Normalizer
Handles all broker variations of MT5 symbols

Author: BLESSING OMOREGIE (Enhanced by QDev Team)
GitHub: Nixiestone
Repository: nyx_trial

Location: src/utils/symbol_normalizer.py
"""

import re
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class SymbolInfo:
    """Normalized symbol information."""
    normalized: str  # Standard form (e.g., "XAUUSD")
    original: str    # As provided by broker
    base: str        # Base currency/asset
    quote: str       # Quote currency
    symbol_type: str # forex, metal, crypto, index
    broker_suffix: str  # Any broker-specific suffix


class SymbolNormalizer:
    """
    Production-grade symbol normalizer for MT5 brokers.
    
    Handles variations like:
    - XAUUSDm, XAUUSDc, XAUUSD.a, XAUUSD_sb
    - EURUSDpro, EURUSD.raw, EURUSD_ecn
    - US30.cash, NAS100.f, SPX500mini
    """
    
    # Core symbol mappings (base forms)
    CORE_SYMBOLS = {
        # Major Forex Pairs
        'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
        # Cross Pairs
        'EURJPY', 'GBPJPY', 'EURGBP', 'AUDJPY', 'EURAUD', 'EURCHF', 'AUDNZD',
        'NZDJPY', 'GBPAUD', 'GBPCAD', 'EURNZD', 'AUDCAD', 'GBPCHF', 'AUDCHF',
        'EURCAD', 'CADJPY', 'GBPNZD', 'CADCHF', 'CHFJPY', 'NZDCAD', 'NZDCHF',
        # Metals
        'XAUUSD', 'XAGUSD', 'XAUEUR', 'XAUGBP', 'XAUAUD', 'XAUJPY',
        # Crypto (if broker supports)
        'BTCUSD', 'ETHUSD', 'LTCUSD', 'XRPUSD', 'BCHUSD', 'ADAUSD',
        # Indices
        'US30', 'NAS100', 'SPX500', 'US500', 'GER40', 'UK100', 'FRA40',
        'ESP35', 'ITA40', 'AUS200', 'JPN225', 'HKG50', 'CHINAH'
    }
    
    # Alternative names mapping
    ALTERNATIVE_NAMES = {
        # Metals
        'GOLD': 'XAUUSD',
        'SILVER': 'XAGUSD',
        'XAUUSD.': 'XAUUSD',  # Handle trailing dots
        'XAGUSD.': 'XAGUSD',
        
        # Indices
        'DOW': 'US30',
        'DOWJONES': 'US30',
        'DJ30': 'US30',
        'NASDAQ': 'NAS100',
        'NDX': 'NAS100',
        'SPX': 'SPX500',
        'SP500': 'SPX500',
        'DAX': 'GER40',
        'FTSE': 'UK100',
        'CAC': 'FRA40',
        'NIKKEI': 'JPN225',
        
        # Crypto alternatives
        'BITCOIN': 'BTCUSD',
        'ETHEREUM': 'ETHUSD',
    }
    
    # Broker suffix patterns (regex)
    BROKER_SUFFIXES = [
        r'\.raw$',      # .raw
        r'\.a$',        # .a
        r'\.cash$',     # .cash
        r'\.f$',        # .f (futures)
        r'\.spot$',     # .spot
        r'_sb$',        # _sb (swap-based)
        r'_ecn$',       # _ecn
        r'_pro$',       # _pro
        r'mini$',       # mini
        r'micro$',      # micro
        r'm$',          # m (micro)
        r'c$',          # c (classic)
        r'pro$',        # pro
        r'prime$',      # prime
        r'_i$',         # _i (interbank)
    ]
    
    @classmethod
    def normalize(cls, symbol: str) -> SymbolInfo:
        """
        Normalize any broker symbol variation to standard form.
        
        Args:
            symbol: Broker-specific symbol (e.g., "XAUUSDm", "EURUSD.raw")
            
        Returns:
            SymbolInfo with normalized data
            
        Examples:
            >>> normalize("XAUUSDm")
            SymbolInfo(normalized="XAUUSD", original="XAUUSDm", ...)
            >>> normalize("EURUSD.raw")
            SymbolInfo(normalized="EURUSD", original="EURUSD.raw", ...)
        """
        original = symbol.strip()
        working = original.upper()
        broker_suffix = ""
        
        # Step 1: Remove any broker suffixes
        for suffix_pattern in cls.BROKER_SUFFIXES:
            match = re.search(suffix_pattern, working, re.IGNORECASE)
            if match:
                broker_suffix = match.group(0)
                working = working[:match.start()]
                break
        
        # Step 2: Check alternative names
        if working in cls.ALTERNATIVE_NAMES:
            normalized = cls.ALTERNATIVE_NAMES[working]
        # Step 3: Check if already a core symbol
        elif working in cls.CORE_SYMBOLS:
            normalized = working
        # Step 4: Try fuzzy matching for partial matches
        else:
            normalized = cls._fuzzy_match(working)
        
        # Step 5: Extract base and quote
        base, quote, symbol_type = cls._extract_components(normalized)
        
        return SymbolInfo(
            normalized=normalized,
            original=original,
            base=base,
            quote=quote,
            symbol_type=symbol_type,
            broker_suffix=broker_suffix
        )
    
    @classmethod
    def _fuzzy_match(cls, symbol: str) -> str:
        """
        Fuzzy match symbol to core symbols.
        Handles cases like "EURUSDPRO" -> "EURUSD"
        """
        # Try to find core symbol that matches start of input
        for core in sorted(cls.CORE_SYMBOLS, key=len, reverse=True):
            if symbol.startswith(core):
                return core
        
        # If no match, return as-is (validation will catch it)
        return symbol
    
    @classmethod
    def _extract_components(cls, symbol: str) -> Tuple[str, str, str]:
        """
        Extract base currency, quote currency, and symbol type.
        
        Returns:
            Tuple of (base, quote, symbol_type)
        """
        # Forex pairs (6 characters, all letters)
        if len(symbol) == 6 and symbol.isalpha():
            return symbol[:3], symbol[3:6], "forex"
        
        # Metals (starts with X)
        elif symbol.startswith('XAU'):
            return "XAU", symbol[3:6], "metal"
        elif symbol.startswith('XAG'):
            return "XAG", symbol[3:6], "metal"
        
        # Crypto (ends with USD/USDT)
        elif symbol.endswith('USDT'):
            return symbol[:-4], "USDT", "crypto"
        elif symbol.endswith('USD') and len(symbol) > 6:
            return symbol[:-3], "USD", "crypto"
        
        # Indices (contains numbers)
        elif any(c.isdigit() for c in symbol):
            return symbol, "", "index"
        
        # Unknown
        else:
            return symbol, "", "unknown"
    
    @classmethod
    def is_valid_normalized(cls, symbol: str) -> bool:
        """
        Check if symbol is a valid normalized form.
        
        Args:
            symbol: Symbol to validate
            
        Returns:
            True if valid normalized symbol
        """
        return symbol.upper() in cls.CORE_SYMBOLS
    
    @classmethod
    def get_pip_value(cls, symbol: str) -> float:
        """
        Get pip value for normalized symbol.
        
        Args:
            symbol: Normalized symbol
            
        Returns:
            Pip value (0.01, 0.0001, 1.0, etc.)
        """
        normalized = cls.normalize(symbol).normalized
        
        # JPY pairs
        if 'JPY' in normalized:
            return 0.01
        
        # Gold
        elif normalized in ['XAUUSD', 'XAUEUR', 'XAUGBP']:
            return 0.01
        
        # Silver
        elif normalized.startswith('XAG'):
            return 0.001
        
        # Indices
        elif any(char.isdigit() for char in normalized):
            return 1.0
        
        # Crypto
        elif normalized in ['BTCUSD', 'ETHUSD', 'LTCUSD', 'XRPUSD', 'BCHUSD']:
            return 1.0
        
        # Standard forex
        else:
            return 0.0001
    
    @classmethod
    def get_display_name(cls, symbol: str) -> str:
        """
        Get user-friendly display name.
        
        Args:
            symbol: Any symbol format
            
        Returns:
            Display name (e.g., "XAU/USD", "EUR/USD")
        """
        info = cls.normalize(symbol)
        normalized = info.normalized
        
        # Forex and metals with slash
        if info.symbol_type in ['forex', 'metal'] and info.quote:
            return f"{info.base}/{info.quote}"
        
        # Crypto with slash
        elif info.symbol_type == 'crypto' and info.quote:
            return f"{info.base}/{info.quote}"
        
        # Indices as-is
        else:
            return normalized
    
    @classmethod
    def batch_normalize(cls, symbols: list) -> Dict[str, SymbolInfo]:
        """
        Normalize multiple symbols at once.
        
        Args:
            symbols: List of symbols to normalize
            
        Returns:
            Dictionary mapping original -> SymbolInfo
        """
        return {sym: cls.normalize(sym) for sym in symbols}


# Convenience functions for backward compatibility
def normalize_symbol(symbol: str) -> str:
    """Quick normalize - returns just the normalized symbol string."""
    return SymbolNormalizer.normalize(symbol).normalized


def get_symbol_info(symbol: str) -> SymbolInfo:
    """Get full symbol information."""
    return SymbolNormalizer.normalize(symbol)


if __name__ == "__main__":
    # Comprehensive test suite
    print("=" * 70)
    print("SYMBOL NORMALIZER - PRODUCTION TEST SUITE")
    print("=" * 70)
    
    test_cases = [
        # Gold variations
        ("XAUUSDm", "XAUUSD"),
        ("XAUUSDc", "XAUUSD"),
        ("XAUUSD.a", "XAUUSD"),
        ("XAUUSD_sb", "XAUUSD"),
        ("GOLD", "XAUUSD"),
        ("XAUUSDpro", "XAUUSD"),
        
        # Forex variations
        ("EURUSD.raw", "EURUSD"),
        ("EURUSDpro", "EURUSD"),
        ("EURUSD_ecn", "EURUSD"),
        ("EURUSDmini", "EURUSD"),
        ("EURUSD", "EURUSD"),
        
        # JPY pairs
        ("USDJPYm", "USDJPY"),
        ("GBPJPY.raw", "GBPJPY"),
        
        # Indices
        ("US30.cash", "US30"),
        ("NAS100.f", "NAS100"),
        ("SPX500mini", "SPX500"),
        ("DOW", "US30"),
        ("NASDAQ", "NAS100"),
        
        # Crypto
        ("BTCUSDm", "BTCUSD"),
        ("BITCOIN", "BTCUSD"),
        
        # Edge cases
        ("XAUUSD.", "XAUUSD"),  # Trailing dot
        ("xauusdm", "XAUUSD"),  # Lowercase
    ]
    
    print("\nTest Cases:")
    print("-" * 70)
    
    passed = 0
    failed = 0
    
    for original, expected in test_cases:
        result = normalize_symbol(original)
        status = "PASS" if result == expected else "FAIL"
        
        if status == "PASS":
            passed += 1
            marker = "✓"
        else:
            failed += 1
            marker = "✗"
        
        print(f"{marker} {original:20} -> {result:10} (expected: {expected:10}) [{status}]")
    
    print("-" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    
    # Additional info test
    print("\n" + "=" * 70)
    print("DETAILED SYMBOL INFO")
    print("=" * 70)
    
    test_symbols = ["XAUUSDm", "EURUSD.raw", "US30.cash", "BTCUSDpro"]
    
    for sym in test_symbols:
        info = get_symbol_info(sym)
        print(f"\nOriginal: {info.original}")
        print(f"  Normalized: {info.normalized}")
        print(f"  Base/Quote: {info.base}/{info.quote}")
        print(f"  Type: {info.symbol_type}")
        print(f"  Broker Suffix: {info.broker_suffix or 'None'}")
        print(f"  Display: {SymbolNormalizer.get_display_name(sym)}")
        print(f"  Pip Value: {SymbolNormalizer.get_pip_value(sym)}")
    
    print("\n" + "=" * 70)
    print("All tests completed!")
    print("=" * 70)