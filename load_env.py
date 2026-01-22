import os
from pathlib import Path
from dotenv import load_dotenv


def load_environment():
    """
    Load environment variables from .env and secrets.env files.
    This MUST run before any imports of config.settings or security modules.
    """
    
    # Get project root
    root_dir = Path(__file__).parent
    
    # Load .env first (if exists)
    env_file = root_dir / '.env'
    if env_file.exists():
        load_dotenv(env_file, override=True)
        print(f"Loaded environment from: {env_file}")
    
    # Load config/secrets.env (priority)
    secrets_file = root_dir / 'config' / 'secrets.env'
    if secrets_file.exists():
        load_dotenv(secrets_file, override=True)
        print(f"Loaded environment from: {secrets_file}")
    
    # Verify MASTER_KEY is loaded
    master_key = os.getenv('MASTER_KEY')
    if master_key:
        print(f"SUCCESS: MASTER_KEY loaded ({len(master_key)} characters)")
    else:
        print("WARNING: MASTER_KEY not found in environment files")
        print("Please ensure MASTER_KEY is set in config/secrets.env")
    
    return master_key is not None


# Auto-load when this module is imported
if __name__ != "__main__":
    load_environment()