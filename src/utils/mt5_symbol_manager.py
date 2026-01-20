"""
MT5 Symbol Auto-Enabler
Automatically enables symbols in Market Watch and discovers working symbols

Author: BLESSING OMOREGIE (Enhanced by QDev Team)
Location: src/utils/mt5_symbol_manager.py (CREATE NEW FILE)
"""

import MetaTrader5 as mt5
from typing import List, Tuple, Dict
from ..utils.logger import get_logger


class MT5SymbolManager:
    """
    Manages MT5 symbols - enables them in Market Watch and discovers available ones.
    """
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger(__name__, config.LOG_LEVEL, config.LOG_FILE_PATH)
        self.enabled_symbols = []
    
    def enable_symbol(self, symbol: str) -> bool:
        """
        Enable a symbol in MT5 Market Watch.
        
        Args:
            symbol: Symbol name to enable
            
        Returns:
            True if successful
        """
        try:
            # Check if symbol exists
            symbol_info = mt5.symbol_info(symbol)
            
            if symbol_info is None:
                self.logger.warning(f"Symbol {symbol} not found on broker")
                return False
            
            # Enable symbol if not visible
            if not symbol_info.visible:
                if not mt5.symbol_select(symbol, True):
                    self.logger.error(f"Failed to enable {symbol}: {mt5.last_error()}")
                    return False
                
                self.logger.info(f"Enabled symbol: {symbol}")
            
            self.enabled_symbols.append(symbol)
            return True
            
        except Exception as e:
            self.logger.exception(f"Error enabling symbol {symbol}: {e}")
            return False
    
    def enable_all_configured_symbols(self, symbols: List[str]) -> Tuple[List[str], List[str]]:
        """
        Enable all configured trading symbols.
        
        Args:
            symbols: List of symbol names to enable
            
        Returns:
            Tuple of (successful_symbols, failed_symbols)
        """
        successful = []
        failed = []
        
        self.logger.info(f"Enabling {len(symbols)} symbols in Market Watch...")
        
        for symbol in symbols:
            if self.enable_symbol(symbol):
                successful.append(symbol)
            else:
                failed.append(symbol)
        
        self.logger.info(f"Enabled {len(successful)}/{len(symbols)} symbols")
        
        if failed:
            self.logger.warning(f"Failed to enable: {', '.join(failed)}")
        
        return successful, failed
    
    def discover_working_symbols(self, test_data: bool = True) -> Dict[str, List[str]]:
        """
        Discover all available and working symbols on the broker.
        
        Args:
            test_data: If True, test if data can be retrieved
            
        Returns:
            Dictionary categorizing symbols by type
        """
        from ..utils.symbol_normalizer import SymbolNormalizer
        
        self.logger.info("Discovering available symbols on broker...")
        
        # Get all symbols
        all_symbols = mt5.symbols_get()
        
        if not all_symbols:
            self.logger.error("Could not retrieve symbols from broker")
            return {}
        
        categories = {
            'forex_major': [],
            'forex_minor': [],
            'metals': [],
            'indices': [],
            'crypto': [],
            'commodities': [],
            'other': []
        }
        
        major_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD']
        
        for symbol in all_symbols:
            name = symbol.name
            
            # Skip if not visible
            if not symbol.visible:
                continue
            
            # Normalize to identify base symbol
            norm_info = SymbolNormalizer.normalize(name)
            base_symbol = norm_info.normalized
            
            # Categorize
            if 'XAU' in base_symbol or 'XAG' in base_symbol or 'GOLD' in base_symbol or 'SILVER' in base_symbol:
                categories['metals'].append(name)
            elif any(idx in base_symbol for idx in ['US30', 'NAS100', 'SPX500', 'GER40', 'UK100', 'JPN225']):
                categories['indices'].append(name)
            elif any(crypto in base_symbol for crypto in ['BTC', 'ETH', 'LTC', 'XRP', 'ADA']):
                categories['crypto'].append(name)
            elif any(comm in base_symbol for comm in ['OIL', 'BRENT', 'WTI', 'GAS']):
                categories['commodities'].append(name)
            elif base_symbol in major_pairs:
                categories['forex_major'].append(name)
            elif len(base_symbol) == 6 and base_symbol.isalpha():
                categories['forex_minor'].append(name)
            else:
                categories['other'].append(name)
        
        # Log summary
        total = sum(len(v) for v in categories.values())
        self.logger.info(f"Discovered {total} visible symbols:")
        for cat, syms in categories.items():
            if syms:
                self.logger.info(f"  {cat}: {len(syms)}")
        
        return categories
    
    def auto_configure_symbols(self, connector) -> List[str]:
        """
        Automatically discover and configure working symbols.
        
        Args:
            connector: MT5Connector instance
            
        Returns:
            List of working symbols
        """
        self.logger.info("Auto-configuring symbols...")
        
        # Discover available symbols
        categories = self.discover_working_symbols()
        
        # Test which symbols have data
        working_symbols = []
        priority_order = ['forex_major', 'metals', 'indices', 'forex_minor', 'crypto']
        
        for category in priority_order:
            symbols = categories.get(category, [])
            
            for symbol in symbols[:5]:  # Test up to 5 per category
                try:
                    # Try to get data
                    df = connector.get_historical_data(symbol, "H1", 10)
                    
                    if df is not None and len(df) > 0:
                        working_symbols.append(symbol)
                        self.logger.info(f"✓ {symbol} - Working")
                        
                        # Limit total symbols
                        if len(working_symbols) >= 10:
                            break
                except:
                    continue
            
            if len(working_symbols) >= 10:
                break
        
        if working_symbols:
            self.logger.info(f"Auto-configured {len(working_symbols)} working symbols")
        else:
            self.logger.warning("No working symbols found - markets may be closed")
        
        return working_symbols
    
    def validate_symbols(self, symbols: List[str], connector) -> Tuple[List[str], List[str]]:
        """
        Validate that symbols can retrieve data.
        
        Args:
            symbols: List of symbols to validate
            connector: MT5Connector instance
            
        Returns:
            Tuple of (working_symbols, broken_symbols)
        """
        self.logger.info(f"Validating {len(symbols)} symbols...")
        
        working = []
        broken = []
        
        for symbol in symbols:
            try:
                df = connector.get_historical_data(symbol, "H1", 10)
                
                if df is not None and len(df) > 0:
                    working.append(symbol)
                    self.logger.debug(f"✓ {symbol} validated")
                else:
                    broken.append(symbol)
                    self.logger.warning(f"✗ {symbol} - No data available")
            except Exception as e:
                broken.append(symbol)
                self.logger.warning(f"✗ {symbol} - Error: {str(e)[:50]}")
        
        self.logger.info(f"Validation complete: {len(working)}/{len(symbols)} working")
        
        return working, broken
    
    def get_enabled_symbols(self) -> List[str]:
        """Get list of symbols that were enabled."""
        return self.enabled_symbols.copy()


if __name__ == "__main__":
    # Test symbol manager
    from config.settings import settings
    from src.data.mt5_connector import MT5Connector
    
    print("Testing MT5 Symbol Manager...")
    
    connector = MT5Connector(settings)
    connector.connect()
    
    manager = MT5SymbolManager(settings)
    
    # Test enabling symbols
    test_symbols = ["EURUSD", "GBPUSD", "XAUUSD"]
    successful, failed = manager.enable_all_configured_symbols(test_symbols)
    
    print(f"\nEnabled: {successful}")
    print(f"Failed: {failed}")
    
    # Discover symbols
    categories = manager.discover_working_symbols()
    print(f"\nCategories found: {list(categories.keys())}")
    
    # Auto-configure
    working = manager.auto_configure_symbols(connector)
    print(f"\nAuto-configured symbols: {working}")
    
    connector.disconnect()
    print("\nSymbol Manager test completed!")