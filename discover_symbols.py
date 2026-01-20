"""
MT5 Symbol Finder and Validator
Discovers available symbols on your broker and updates configuration

Author: BLESSING OMOREGIE 
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import MetaTrader5 as mt5
from config.settings import settings
from src.data.mt5_connector import MT5Connector
from src.utils.symbol_normalizer import SymbolNormalizer


def find_available_symbols(connector: MT5Connector):
    """
    Discover all available symbols on your broker.
    
    Returns:
        Dictionary organized by category
    """
    print("\nDiscovering available symbols on your broker...")
    print("=" * 70)
    
    # Get all symbols
    all_symbols = mt5.symbols_get()
    
    if not all_symbols:
        print("ERROR: Could not retrieve symbols from MT5")
        return None
    
    # Categorize symbols
    categories = {
        'forex_major': [],
        'forex_minor': [],
        'forex_exotic': [],
        'metals': [],
        'indices': [],
        'crypto': [],
        'other': []
    }
    
    major_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD']
    
    for symbol in all_symbols:
        name = symbol.name
        
        # Normalize to identify base symbol
        norm_info = SymbolNormalizer.normalize(name)
        base_symbol = norm_info.normalized
        
        # Skip if not visible
        if not symbol.visible:
            continue
        
        # Categorize
        if 'XAU' in base_symbol or 'XAG' in base_symbol or 'GOLD' in base_symbol or 'SILVER' in base_symbol:
            categories['metals'].append((name, base_symbol))
        elif any(idx in base_symbol for idx in ['US30', 'NAS100', 'SPX500', 'GER40', 'UK100']):
            categories['indices'].append((name, base_symbol))
        elif any(crypto in base_symbol for crypto in ['BTC', 'ETH', 'LTC', 'XRP']):
            categories['crypto'].append((name, base_symbol))
        elif base_symbol in major_pairs:
            categories['forex_major'].append((name, base_symbol))
        elif len(base_symbol) == 6 and base_symbol.isalpha():
            # Other forex pairs
            if 'USD' in base_symbol or 'EUR' in base_symbol or 'GBP' in base_symbol:
                categories['forex_minor'].append((name, base_symbol))
            else:
                categories['forex_exotic'].append((name, base_symbol))
        else:
            categories['other'].append((name, base_symbol))
    
    return categories


def test_symbol_data(connector: MT5Connector, symbol_name: str) -> bool:
    """
    Test if we can retrieve data for a symbol.
    
    Returns:
        True if data retrieval successful
    """
    try:
        # Try to get 10 candles
        df = connector.get_historical_data(symbol_name, "H1", 10)
        
        if df is not None and len(df) > 0:
            return True
        return False
    except:
        return False


def main():
    """Main symbol discovery function."""
    
    print("=" * 70)
    print("MT5 SYMBOL FINDER & VALIDATOR")
    print("=" * 70)
    
    # Connect to MT5
    print("\n[1/3] Connecting to MT5...")
    connector = MT5Connector(settings)
    
    if not connector.connect():
        print("ERROR: Could not connect to MT5")
        return
    
    print("Connected successfully!")
    
    # Find symbols
    print("\n[2/3] Discovering symbols...")
    categories = find_available_symbols(connector)
    
    if not categories:
        connector.disconnect()
        return
    
    # Display results
    print("\n[3/3] Testing symbols and generating recommendations...")
    print("=" * 70)
    
    working_symbols = []
    
    for category, symbols in categories.items():
        if not symbols:
            continue
        
        print(f"\n{category.upper().replace('_', ' ')} ({len(symbols)} found):")
        print("-" * 70)
        
        for broker_name, normalized in symbols[:10]:  # Test first 10 in each category
            # Test if we can get data
            works = test_symbol_data(connector, broker_name)
            status = "OK" if works else "FAIL"
            marker = "✓" if works else "✗"
            
            print(f"{marker} {broker_name:<20} (normalizes to: {normalized:<10}) [{status}]")
            
            if works:
                working_symbols.append(broker_name)
    
    # Generate recommended configuration
    print("\n" + "=" * 70)
    print("RECOMMENDED CONFIGURATION")
    print("=" * 70)
    
    if working_symbols:
        print("\nAdd these symbols to config/settings.py:")
        print("\nTRADING_SYMBOLS: List[str] = [")
        
        # Prioritize important symbols
        priority_patterns = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'BTCUSD', 'US30']
        
        # Add priority symbols first
        for pattern in priority_patterns:
            for symbol in working_symbols:
                norm = SymbolNormalizer.normalize(symbol).normalized
                if pattern in norm and symbol not in [s for s in working_symbols[:5]]:
                    print(f'    "{symbol}",  # {norm}')
                    working_symbols.remove(symbol)
                    break
        
        # Add remaining symbols (up to 10 total)
        for symbol in working_symbols[:5]:
            norm = SymbolNormalizer.normalize(symbol).normalized
            print(f'    "{symbol}",  # {norm}')
        
        print("]")
        
        print("\n" + "=" * 70)
        print("SYMBOL TESTING COMPLETE")
        print("=" * 70)
        print(f"\nTotal symbols found: {sum(len(s) for s in categories.values())}")
        print(f"Working symbols: {len(working_symbols)}")
        
        # Save to file for reference
        output_file = "working_symbols.txt"
        with open(output_file, 'w') as f:
            f.write("WORKING SYMBOLS FOR YOUR BROKER\n")
            f.write("=" * 70 + "\n\n")
            for symbol in working_symbols:
                norm = SymbolNormalizer.normalize(symbol).normalized
                f.write(f"{symbol} -> {norm}\n")
        
        print(f"\nFull list saved to: {output_file}")
    else:
        print("\nWARNING: No working symbols found!")
        print("Possible issues:")
        print("  1. Market is closed (Forex closes Friday evening to Sunday)")
        print("  2. Demo account has limited symbols")
        print("  3. Symbols need to be added in MT5 Market Watch")
        
        print("\nTo add symbols in MT5:")
        print("  1. Open MT5 terminal")
        print("  2. Right-click Market Watch")
        print("  3. Select 'Symbols'")
        print("  4. Find and enable symbols you want to trade")
    
    # Disconnect
    connector.disconnect()
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()