"""
Secure Environment Loader - PRODUCTION READY
Validates all credentials before bot starts
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv


def load_environment():
    """
    Load and validate all environment variables.
    FAILS FAST if critical variables missing.
    """
    root_dir = Path(__file__).parent
    
    # Load environment files in order
    env_files = [
        root_dir / '.env',
        root_dir / 'config' / 'secrets.env'
    ]
    
    for env_file in env_files:
        if env_file.exists():
            load_dotenv(env_file, override=True)
            print(f"✓ Loaded: {env_file.name}")
    
    # CRITICAL: Validate MASTER_KEY
    master_key = os.getenv('MASTER_KEY', '').strip()
    
    if not master_key or len(master_key) < 32:
        print("\n" + "="*70)
        print("FATAL ERROR: MASTER_KEY not configured properly")
        print("="*70)
        print("\nREQUIRED: Set MASTER_KEY with at least 32 characters")
        print("\nSteps to fix:")
        print("  1. Open config/secrets.env")
        print("  2. Set: MASTER_KEY=your-secure-32-character-password-here")
        print("  3. Save file and restart")
        print("="*70)
        sys.exit(1)
    
    # Validate MT5 credentials
    mt5_login = os.getenv('MT5_LOGIN', '0')
    mt5_password = os.getenv('MT5_PASSWORD', '')
    mt5_server = os.getenv('MT5_SERVER', '')
    
    if mt5_login == '0' or not mt5_password or not mt5_server:
        print("\n" + "="*70)
        print("WARNING: MT5 credentials not fully configured")
        print("="*70)
        print("Set in config/secrets.env:")
        print("  MT5_LOGIN=your_account_number")
        print("  MT5_PASSWORD=your_password")
        print("  MT5_SERVER=your_server_name")
        print("="*70)
    
    # Validate Telegram
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    telegram_chat = os.getenv('TELEGRAM_CHAT_ID', '')
    
    if not telegram_token or not telegram_chat:
        print("\n" + "="*70)
        print("WARNING: Telegram not configured")
        print("="*70)
        print("Set in config/secrets.env:")
        print("  TELEGRAM_BOT_TOKEN=your_bot_token")
        print("  TELEGRAM_CHAT_ID=your_chat_id")
        print("="*70)
    
    print(f"\n✓ Environment validated successfully")
    print(f"✓ MASTER_KEY: {len(master_key)} characters")
    
    return True


if __name__ == "__main__":
    load_environment()