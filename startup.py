"""
Production Startup Script
Ensures all symbols are enabled and bot is ready

Author: BLESSING OMOREGIE (Enhanced by QDev Team)
Location: startup.py (CREATE NEW FILE in root)
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import settings, validate_settings
from src.data.mt5_connector import MT5Connector
from src.utils.mt5_symbol_manager import MT5SymbolManager


def startup_checks():
    """Run all startup checks and symbol enablement."""
    
    print("=" * 70)
    print("NYX TRADING BOT - PRODUCTION STARTUP")
    print("=" * 70)
    
    # Step 1: Validate configuration
    print("\n[1/5] Validating configuration...")
    if not validate_settings():
        print("ERROR: Configuration validation failed")
        return False
    print("SUCCESS: Configuration valid")
    
    # Step 2: Connect to MT5
    print("\n[2/5] Connecting to MT5...")
    connector = MT5Connector(settings)
    
    if not connector.connect():
        print("ERROR: Failed to connect to MT5")
        return False
    print("SUCCESS: Connected to MT5")
    
    # Step 3: Initialize symbol manager
    print("\n[3/5] Initializing symbol manager...")
    symbol_manager = MT5SymbolManager(settings)
    
    # Step 4: Enable all configured symbols
    print("\n[4/5] Enabling trading symbols in Market Watch...")
    successful, failed = symbol_manager.enable_all_configured_symbols(
        settings.TRADING_SYMBOLS
    )
    
    if successful:
        print(f"SUCCESS: Enabled {len(successful)} symbols")
        for sym in successful:
            print(f"  - {sym}")
    
    if failed:
        print(f"\nWARNING: Failed to enable {len(failed)} symbols:")
        for sym in failed:
            print(f"  - {sym}")
        
        # Try to auto-discover working symbols
        print("\n[4b/5] Auto-discovering working symbols...")
        working = symbol_manager.auto_configure_symbols(connector)
        
        if working:
            print(f"SUCCESS: Auto-discovered {len(working)} working symbols")
            # Update settings
            settings.TRADING_SYMBOLS = working
    
    # Step 5: Validate all symbols can retrieve data
    print("\n[5/5] Validating symbol data access...")
    final_symbols = settings.TRADING_SYMBOLS if successful else working if working else []
    
    if not final_symbols:
        print("ERROR: No working symbols available")
        connector.disconnect()
        return False
    
    working_symbols, broken_symbols = symbol_manager.validate_symbols(
        final_symbols,
        connector
    )
    
    if working_symbols:
        print(f"SUCCESS: {len(working_symbols)} symbols validated")
        settings.TRADING_SYMBOLS = working_symbols
    
    if broken_symbols:
        print(f"WARNING: {len(broken_symbols)} symbols failed validation:")
        for sym in broken_symbols:
            print(f"  - {sym}")
    
    # Disconnect
    connector.disconnect()
    
    # Final report
    print("\n" + "=" * 70)
    print("STARTUP COMPLETE")
    print("=" * 70)
    print(f"\nActive Trading Symbols: {len(settings.TRADING_SYMBOLS)}")
    for sym in settings.TRADING_SYMBOLS:
        print(f"  - {sym}")
    
    print(f"\nAuto Trading: {'ENABLED' if settings.AUTO_TRADING_ENABLED else 'DISABLED'}")
    print(f"Environment: {settings.ENVIRONMENT}")
    
    print("\n" + "=" * 70)
    
    return True


if __name__ == "__main__":
    success = startup_checks()
    
    if success:
        print("\nBot is ready to run!")
        print("Execute: python main.py")
        sys.exit(0)
    else:
        print("\nStartup failed. Please fix errors above.")
        sys.exit(1)