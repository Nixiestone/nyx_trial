"""
Database Initialization Script - FIXED VERSION
Creates all tables and sets up initial admin user

Author: Elite QDev Team
Location: scripts/init_database.py (REPLACE ENTIRE FILE)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# CRITICAL: Load environment FIRST
import load_env
load_env.load_environment()

# Now import everything else
from config.settings import settings
from src.database.models import Base, User, UserRole
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os


def init_database():
    """Initialize database with all tables."""
    
    print("=" * 70)
    print("DATABASE INITIALIZATION")
    print("=" * 70)
    
    # Step 1: Create data directory
    print("\n[1/5] Creating data directory...")
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    print(f"Created: {data_dir.absolute()}")
    
    # Step 2: Create database engine
    print("\n[2/5] Creating database engine...")
    try:
        engine = create_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )
        print(f"Database URL: {settings.DATABASE_URL}")
    except Exception as e:
        print(f"ERROR: Failed to create engine: {e}")
        return False
    
    # Step 3: Create all tables
    print("\n[3/5] Creating database tables...")
    try:
        Base.metadata.create_all(engine)
        print("SUCCESS: All tables created")
        print("Tables:")
        for table in Base.metadata.sorted_tables:
            print(f"  - {table.name}")
    except Exception as e:
        print(f"ERROR: Failed to create tables: {e}")
        return False
    
    # Step 4: Create session
    print("\n[4/5] Creating database session...")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Step 5: Create initial admin user
    print("\n[5/5] Creating initial admin user...")
    
    try:
        admin_chat_id = int(settings.TELEGRAM_CHAT_ID) if settings.TELEGRAM_CHAT_ID else None
        
        if not admin_chat_id:
            print("WARNING: TELEGRAM_CHAT_ID not set in secrets.env")
            print("Skipping admin user creation")
            print("\nSet TELEGRAM_CHAT_ID in config/secrets.env and run again")
        else:
            existing_admin = session.query(User).filter_by(
                telegram_chat_id=admin_chat_id
            ).first()
            
            if existing_admin:
                print(f"Admin user already exists: {existing_admin.first_name}")
                print(f"Chat ID: {admin_chat_id}")
                print(f"Role: {existing_admin.role.value}")
            else:
                admin = User(
                    telegram_chat_id=admin_chat_id,
                    role=UserRole.ADMIN,
                    first_name="Admin",
                    is_active=True,
                    notifications_enabled=True,
                    auto_trade_enabled=False
                )
                session.add(admin)
                session.commit()
                
                print(f"SUCCESS: Admin user created")
                print(f"Chat ID: {admin_chat_id}")
                print(f"Role: ADMIN")
                print(f"\nImportant: Start a conversation with your bot to activate")
    
    except Exception as e:
        print(f"ERROR: Failed to create admin user: {e}")
        session.rollback()
    finally:
        session.close()
    
    # Final report
    print("\n" + "=" * 70)
    print("DATABASE INITIALIZATION COMPLETE")
    print("=" * 70)
    print("\nDatabase file created at:")
    
    if "sqlite:///" in settings.DATABASE_URL:
        db_file = settings.DATABASE_URL.replace("sqlite:///", "")
        db_path = Path(db_file).absolute()
        print(f"  {db_path}")
        
        if db_path.exists():
            file_size = db_path.stat().st_size
            print(f"  Size: {file_size} bytes")
    
    print("\nNext steps:")
    print("  1. Run: python test_mt5_connection.py")
    print("  2. Run: python main.py")
    
    return True


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)