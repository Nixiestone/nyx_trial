"""
CRITICAL: Environment Loader - Must Run FIRST
Location: env_loader.py (CREATE IN ROOT)

This MUST be imported before ANY other project imports.
Author: Elite QDev Team - DevOps Engineer
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv


def load_all_env_files():
    """
    Load ALL environment files in correct order.
    MUST be called before any other imports.
    """
    root_dir = Path(__file__).parent
    
    # Load in priority order
    env_files = [
        root_dir / '.env',
        root_dir / 'config' / 'secrets.env'
    ]
    
    for env_file in env_files:
        if env_file.exists():
            load_dotenv(env_file, override=True)
            print(f"[ENV] Loaded: {env_file}")
    
    # Verify MASTER_KEY
    master_key = os.getenv('MASTER_KEY')
    
    if not master_key:
        print("\n" + "="*70)
        print("ERROR: MASTER_KEY not found in environment")
        print("="*70)
        print("\nYou must set MASTER_KEY in one of these files:")
        print("  1. .env (in root directory)")
        print("  2. config/secrets.env")
        print("\nExample:")
        print("  MASTER_KEY=your_secure_key_minimum_32_characters")
        print("="*70)
        sys.exit(1)
    
    if len(master_key) < 16:
        print("\n" + "="*70)
        print(f"WARNING: MASTER_KEY too short ({len(master_key)} chars)")
        print("="*70)
        print("For production security, use at least 32 characters")
        print("="*70)
    
    print(f"[ENV] MASTER_KEY loaded successfully ({len(master_key)} chars)")
    
    return True


# Auto-execute on import
if __name__ != "__main__":
    load_all_env_files()