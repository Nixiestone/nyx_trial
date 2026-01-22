"""
Production User Manager
Handles user-level operations and preferences

Location: src/core/user_manager.py (CREATE NEW FILE)
Author: Elite QDev Team
"""

from sqlalchemy.orm import Session
from src.database.models import User, MT5Account, Trade, UserRole
from src.utils.logger import get_logger
from typing import Dict, Optional, List
from datetime import datetime, timedelta


class UserManager:
    """
    Production-grade user management for:
    - User profile management
    - Preference handling
    - Activity tracking
    - Performance analytics per user
    """
    
    def __init__(self, config, db_session: Session):
        self.config = config
        self.db = db_session
        self.logger = get_logger(__name__, config.LOG_LEVEL, config.LOG_FILE_PATH)
    
    # ==================== USER OPERATIONS ====================
    
    def get_or_create_user(
        self,
        telegram_chat_id: int,
        username: str = None,
        first_name: str = None,
        last_name: str = None
    ) -> User:
        """
        Get existing user or create new one.
        
        Args:
            telegram_chat_id: Telegram chat ID
            username: Telegram username
            first_name: User's first name
            last_name: User's last name
            
        Returns:
            User object
        """
        try:
            # Try to get existing user
            user = self.db.query(User).filter_by(
                telegram_chat_id=telegram_chat_id
            ).first()
            
            if user:
                # Update last active
                user.last_active = datetime.utcnow()
                
                # Update username if changed
                if username and user.telegram_username != username:
                    user.telegram_username = username
                
                self.db.commit()
                
                self.logger.info(f"User {telegram_chat_id} logged in")
                return user
            
            # Create new user
            user = User(
                telegram_chat_id=telegram_chat_id,
                telegram_username=username,
                first_name=first_name,
                last_name=last_name,
                role=UserRole.USER,
                is_active=True,
                notifications_enabled=True,
                auto_trade_enabled=False
            )
            
            self.db.add(user)
            self.db.commit()
            
            self.logger.info(f"New user created: {telegram_chat_id}")
            
            return user
            
        except Exception as e:
            self.logger.exception(f"Error in get_or_create_user: {e}")
            self.db.rollback()
            return None
    
    def update_user_preferences(
        self,
        user_id: int,
        notifications_enabled: bool = None,
        auto_trade_enabled: bool = None
    ) -> bool:
        """
        Update user preferences.
        
        Args:
            user_id: User ID
            notifications_enabled: Enable/disable notifications
            auto_trade_enabled: Enable/disable auto-trading
            
        Returns:
            True if successful
        """
        try:
            user = self.db.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False
            
            if notifications_enabled is not None:
                user.notifications_enabled = notifications_enabled
            
            if auto_trade_enabled is not None:
                user.auto_trade_enabled = auto_trade_enabled
            
            self.db.commit()
            
            self.logger.info(f"User {user_id} preferences updated")
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Error updating preferences: {e}")
            self.db.rollback()
            return False
    
    def get_user_profile(self, user_id: int) -> Optional[Dict]:
        """
        Get complete user profile with statistics.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with user profile data
        """
        try:
            user = self.db.query(User).filter_by(id=user_id).first()
            
            if not user:
                return None
            
            # Get user's accounts
            accounts = self.db.query(MT5Account).filter_by(user_id=user_id).all()
            
            # Get user's trades
            trades = self.db.query(Trade).filter_by(user_id=user_id).all()
            closed_trades = [t for t in trades if t.is_closed]
            
            # Calculate statistics
            total_pnl = sum(t.profit for t in closed_trades if t.profit)
            winners = len([t for t in closed_trades if t.profit and t.profit > 0])
            losers = len([t for t in closed_trades if t.profit and t.profit < 0])
            
            win_rate = (winners / len(closed_trades) * 100) if closed_trades else 0
            
            # Active accounts
            active_accounts = len([a for a in accounts if a.status.value == 'active'])
            
            return {
                'user_id': user.id,
                'telegram_chat_id': user.telegram_chat_id,
                'telegram_username': user.telegram_username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role.value,
                'is_active': user.is_active,
                'notifications_enabled': user.notifications_enabled,
                'auto_trade_enabled': user.auto_trade_enabled,
                'created_at': user.created_at,
                'last_active': user.last_active,
                'total_accounts': len(accounts),
                'active_accounts': active_accounts,
                'total_trades': len(trades),
                'closed_trades': len(closed_trades),
                'open_trades': len(trades) - len(closed_trades),
                'total_pnl': total_pnl,
                'win_rate': win_rate,
                'winners': winners,
                'losers': losers
            }
            
        except Exception as e:
            self.logger.exception(f"Error getting user profile: {e}")
            return None
    
    # ==================== USER ANALYTICS ====================
    
    def get_user_performance_summary(self, user_id: int) -> Dict:
        """
        Get detailed performance summary for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with performance metrics
        """
        try:
            trades = self.db.query(Trade).filter_by(
                user_id=user_id,
                is_closed=True
            ).all()
            
            if not trades:
                return {
                    'total_trades': 0,
                    'no_data': True
                }
            
            # Calculate comprehensive statistics
            total_pnl = sum(t.profit for t in trades if t.profit)
            total_pips = sum(t.pips for t in trades if t.pips)
            
            winners = [t for t in trades if t.profit and t.profit > 0]
            losers = [t for t in trades if t.profit and t.profit < 0]
            
            avg_win = sum(t.profit for t in winners) / len(winners) if winners else 0
            avg_loss = abs(sum(t.profit for t in losers) / len(losers)) if losers else 0
            
            win_rate = (len(winners) / len(trades) * 100) if trades else 0
            
            # Profit factor
            gross_profit = sum(t.profit for t in winners) if winners else 0
            gross_loss = abs(sum(t.profit for t in losers)) if losers else 0
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
            
            # Best and worst trades
            best_trade = max(trades, key=lambda t: t.profit if t.profit else 0)
            worst_trade = min(trades, key=lambda t: t.profit if t.profit else 0)
            
            # Daily performance
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_trades = [t for t in trades if t.close_time and t.close_time >= today_start]
            today_pnl = sum(t.profit for t in today_trades if t.profit)
            
            # Weekly performance
            week_start = datetime.utcnow() - timedelta(days=7)
            week_trades = [t for t in trades if t.close_time and t.close_time >= week_start]
            week_pnl = sum(t.profit for t in week_trades if t.profit)
            
            return {
                'total_trades': len(trades),
                'total_pnl': total_pnl,
                'total_pips': total_pips,
                'winners': len(winners),
                'losers': len(losers),
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'best_trade_pnl': best_trade.profit if best_trade and best_trade.profit else 0,
                'worst_trade_pnl': worst_trade.profit if worst_trade and worst_trade.profit else 0,
                'today_trades': len(today_trades),
                'today_pnl': today_pnl,
                'week_trades': len(week_trades),
                'week_pnl': week_pnl
            }
            
        except Exception as e:
            self.logger.exception(f"Error getting performance summary: {e}")
            return {}
    
    def get_user_daily_report(self, user_id: int) -> Dict:
        """
        Generate daily performance report for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with daily report
        """
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Get today's trades
            today_trades = self.db.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.open_time >= today_start
            ).all()
            
            closed_today = [t for t in today_trades if t.is_closed]
            
            total_pnl = sum(t.profit for t in closed_today if t.profit)
            total_pips = sum(t.pips for t in closed_today if t.pips)
            
            winners = len([t for t in closed_today if t.profit and t.profit > 0])
            losers = len([t for t in closed_today if t.profit and t.profit < 0])
            
            win_rate = (winners / len(closed_today) * 100) if closed_today else 0
            
            return {
                'date': datetime.utcnow().strftime('%Y-%m-%d'),
                'total_trades': len(today_trades),
                'closed_trades': len(closed_today),
                'open_trades': len(today_trades) - len(closed_today),
                'total_pnl': total_pnl,
                'total_pips': total_pips,
                'winners': winners,
                'losers': losers,
                'win_rate': win_rate
            }
            
        except Exception as e:
            self.logger.exception(f"Error generating daily report: {e}")
            return {}
    
    # ==================== ACTIVITY TRACKING ====================
    
    def track_user_activity(self, user_id: int, action: str):
        """
        Track user activity for analytics.
        
        Args:
            user_id: User ID
            action: Action performed
        """
        try:
            user = self.db.query(User).filter_by(id=user_id).first()
            
            if user:
                user.last_active = datetime.utcnow()
                self.db.commit()
                
                self.logger.debug(f"User {user_id} activity: {action}")
            
        except Exception as e:
            self.logger.exception(f"Error tracking activity: {e}")
    
    def get_user_activity_stats(self, user_id: int, days: int = 30) -> Dict:
        """
        Get user activity statistics.
        
        Args:
            user_id: User ID
            days: Number of days to analyze
            
        Returns:
            Dictionary with activity metrics
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get trades in period
            trades = self.db.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.open_time >= cutoff_date
            ).all()
            
            # Get user
            user = self.db.query(User).filter_by(id=user_id).first()
            
            days_since_last_active = (datetime.utcnow() - user.last_active).days if user.last_active else None
            
            return {
                'trades_in_period': len(trades),
                'days_analyzed': days,
                'last_active': user.last_active,
                'days_since_active': days_since_last_active,
                'is_active_trader': len(trades) > 0
            }
            
        except Exception as e:
            self.logger.exception(f"Error getting activity stats: {e}")
            return {}
    
    # ==================== USER UTILITIES ====================
    
    def is_user_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        try:
            user = self.db.query(User).filter_by(id=user_id).first()
            return user and user.role == UserRole.ADMIN
        except:
            return False
    
    def is_user_banned(self, user_id: int) -> bool:
        """Check if user is banned."""
        try:
            user = self.db.query(User).filter_by(id=user_id).first()
            return user and user.role == UserRole.BANNED
        except:
            return False
    
    def get_user_accounts(self, user_id: int) -> List[MT5Account]:
        """Get all accounts for a user."""
        try:
            return self.db.query(MT5Account).filter_by(user_id=user_id).all()
        except Exception as e:
            self.logger.exception(f"Error getting user accounts: {e}")
            return []


if __name__ == "__main__":
    print("User Manager - Production Ready")