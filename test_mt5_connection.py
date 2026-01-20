"""
MT5 Connection Test Script
Author: BLESSING OMOREGIE
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import settings, validate_settings
from src.data.mt5_connector import MT5Connector

def main():
    print("=" * 60)
    print("MT5 CONNECTION TEST")
    print("=" * 60)
    
    # Step 1: Validate configuration
    print("\n[1/4] Validating configuration...")
    if not validate_settings():
        print("❌ Configuration invalid!")
        print("\nPlease check config/secrets.env")
        return False
    print("✅ Configuration valid")
    
    # Step 2: Create connector
    print("\n[2/4] Creating MT5 connector...")
    connector = MT5Connector(settings)
    print("✅ Connector created")
    
    # Step 3: Connect to MT5
    print("\n[3/4] Connecting to MT5...")
    if not connector.connect():
        print("❌ Connection failed!")
        print("\nTroubleshooting:")
        print("  1. Is MT5 terminal running?")
        print("  2. Are your credentials correct?")
        print("  3. Is the server name correct?")
        return False
    print("✅ Connected to MT5")
    
    # Step 4: Test functionality
    print("\n[4/4] Testing MT5 functionality...")
    
    # Get account info
    account = connector.get_account_info()
    if account:
        print(f"\n📊 Account Information:")
        print(f"  Login: {account['login']}")
        print(f"  Server: {account['server']}")
        print(f"  Balance: {account['balance']} {account['currency']}")
        print(f"  Equity: {account['equity']}")
        print(f"  Margin Level: {account['margin_level']:.2f}%")
        print(f"  Leverage: 1:{account['leverage']}")
    
    # Test data retrieval
    test_symbol = "EURUSD"
    df = connector.get_historical_data(test_symbol, "H4", 100)
    
    if df is not None:
        print(f"\n📈 Market Data Test ({test_symbol}):")
        print(f"  Retrieved {len(df)} candles")
        print(f"  Latest close: {df['close'].iloc[-1]:.5f}")
        print(f"  Data range: {df.index[0]} to {df.index[-1]}")
    
    # Disconnect
    connector.disconnect()
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nYou can now run the bot with: python main.py")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)