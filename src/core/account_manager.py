"""
Account Manager - Handles MT5 account connections and management
Author: BLESSING OMOREGIE
"""

from sqlalchemy.orm import Session
from src.database.models import MT5Account, User, AccountStatus
from src.security.encryption import get_encryptor
from src.data.mt5_connector import MT5Connector
from src.utils.logger import get_logger
from typing import Optional, List, Dict
from datetime import datetime

logger = get_logger("AccountManager")


class AccountManager:
    """Manages MT5 accounts for multiple users."""
    
    def __init__(self, config, db_session: Session):
        self.config = config
        self.db = db_session
        self.encryptor = get_encryptor()
        self.logger = logger
        self.active_connections = {}  # account_id -> MT5Connector
    
    def add_account(
        self,
        user_id: int,
        account_name: str,
        mt5_login: int,
        mt5_password: str,
        mt5_server: str
    ) -> Optional[MT5Account]:
        """Add new MT5 account for user."""
        try:
            # Check user account limit
            user = self.db.query(User).filter_by(id=user_id).first()
            if not user:
                raise ValueError("User not found")
            
            existing_count = self.db.query(MT5Account).filter_by(
                user_id=user_id,
                status=AccountStatus.ACTIVE
            ).count()
            
            # Admin has unlimited, users limited to 5
            if user.role.value != 'admin' and existing_count >= 5:
                raise ValueError("Maximum 5 accounts allowed for non-admin users")
            
            # Encrypt password
            encrypted_password = self.encryptor.encrypt(mt5_password)
            
            # Create account record
            account = MT5Account(
                user_id=user_id,
                account_name=account_name,
                mt5_login=mt5_login,
                mt5_server=mt5_server,
                encrypted_password=encrypted_password,
                status=AccountStatus.PENDING
            )
            
            self.db.add(account)
            self.db.commit()
            
            # Test connection
            if self.test_connection(account.id):
                account.status = AccountStatus.ACTIVE
                self.db.commit()
                self.logger.info(f"Account {mt5_login} added successfully for user {user_id}")
                return account
            else:
                account.status = AccountStatus.ERROR
                account.last_error = "Connection test failed"
                self.db.commit()
                return account
        
        except Exception as e:
            self.logger.exception(f"Error adding account: {e}")
            self.db.rollback()
            return None
    
    def test_connection(self, account_id: int) -> bool:
        """Test MT5 connection for an account."""
        try:
            account = self.db.query(MT5Account).filter_by(id=account_id).first()
            if not account:
                return False
            
            # Decrypt password
            password = self.encryptor.decrypt(account.encrypted_password)
            
            # Create connector with account-specific settings
            connector = MT5Connector(self.config)
            
            # Override settings with account-specific values
            connector.config.MT5_LOGIN = account.mt5_login
            connector.config.MT5_PASSWORD = password
            connector.config.MT5_SERVER = account.mt5_server
            
            # Test connection
            if connector.connect():
                # Get account info to update currency and balance
                info = connector.get_account_info()
                if info:
                    account.account_currency = info['currency']
                    account.account_balance = info['balance']
                    account.account_equity = info['equity']
                    account.account_leverage = info['leverage']
                    account.last_connected = datetime.utcnow()
                    self.db.commit()
                
                connector.disconnect()
                return True
            
            return False
        
        except Exception as e:
            self.logger.exception(f"Connection test failed: {e}")
            return False
    
    def get_connector(self, account_id: int) -> Optional[MT5Connector]:
        """Get or create MT5 connector for account."""
        # Return cached connector if exists
        if account_id in self.active_connections:
            connector = self.active_connections[account_id]
            if connector.check_connection():
                return connector
            else:
                # Reconnect
                del self.active_connections[account_id]
        
        # Create new connector
        account = self.db.query(MT5Account).filter_by(id=account_id).first()
        if not account or account.status != AccountStatus.ACTIVE:
            return None
        
        try:
            password = self.encryptor.decrypt(account.encrypted_password)
            
            connector = MT5Connector(self.config)
            connector.config.MT5_LOGIN = account.mt5_login
            connector.config.MT5_PASSWORD = password
            connector.config.MT5_SERVER = account.mt5_server
            
            if connector.connect():
                self.active_connections[account_id] = connector
                return connector
        
        except Exception as e:
            self.logger.exception(f"Error creating connector: {e}")
        
        return None
    
    def get_active_accounts_for_user(self, user_id: int) -> List[MT5Account]:
        """Get all active accounts for a user."""
        return self.db.query(MT5Account).filter_by(
            user_id=user_id,
            status=AccountStatus.ACTIVE
        ).all()
    
    def enable_auto_trade(self, account_id: int, user_id: int) -> bool:
        """Enable auto-trading for an account."""
        try:
            account = self.db.query(MT5Account).filter_by(
                id=account_id,
                user_id=user_id
            ).first()
            
            if not account:
                return False
            
            # Test connection first
            if not self.test_connection(account_id):
                return False
            
            account.auto_trade_enabled = True
            self.db.commit()
            
            self.logger.info(f"Auto-trade enabled for account {account_id}")
            return True
        
        except Exception as e:
            self.logger.exception(f"Error enabling auto-trade: {e}")
            return False