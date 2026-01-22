"""
Production Admin Manager
Handles admin-level operations and user management

Location: src/core/admin_manager.py (CREATE NEW FILE)
Author: Elite QDev Team
"""

from sqlalchemy.orm import Session
from src.database.models import User, MT5Account, Trade, UserRole, AccountStatus, AuditLog
from src.utils.logger import get_logger
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class AdminManager:
    """
    Production-grade admin management system for:
    - User management
    - System monitoring
    - Performance analytics
    - Security auditing
    """
    
    def __init__(self, config, db_session: Session):
        self.config = config
        self.db = db_session
        self.logger = get_logger(__name__, config.LOG_LEVEL, config.LOG_FILE_PATH)
    
    # ==================== USER MANAGEMENT ====================
    
    def get_all_users(self, include_banned: bool = False) -> List[User]:
        """
        Get all users in the system.
        
        Args:
            include_banned: Include banned users
            
        Returns:
            List of User objects
        """
        try:
            query = self.db.query(User)
            
            if not include_banned:
                query = query.filter(User.role != UserRole.BANNED)
            
            users = query.order_by(User.created_at.desc()).all()
            
            self.logger.info(f"Retrieved {len(users)} users")
            return users
            
        except Exception as e:
            self.logger.exception(f"Error getting users: {e}")
            return []
    
    def get_user_stats(self) -> Dict:
        """
        Get comprehensive user statistics.
        
        Returns:
            Dictionary with user metrics
        """
        try:
            total_users = self.db.query(User).count()
            active_users = self.db.query(User).filter_by(is_active=True).count()
            admin_count = self.db.query(User).filter_by(role=UserRole.ADMIN).count()
            banned_count = self.db.query(User).filter_by(role=UserRole.BANNED).count()
            
            # Users with auto-trade enabled
            auto_trade_users = self.db.query(User).filter_by(auto_trade_enabled=True).count()
            
            # New users this week
            week_ago = datetime.utcnow() - timedelta(days=7)
            new_users_week = self.db.query(User).filter(
                User.created_at >= week_ago
            ).count()
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'admin_count': admin_count,
                'banned_count': banned_count,
                'auto_trade_enabled': auto_trade_users,
                'new_users_this_week': new_users_week
            }
            
        except Exception as e:
            self.logger.exception(f"Error getting user stats: {e}")
            return {}
    
    def promote_to_admin(self, user_id: int) -> bool:
        """
        Promote a user to admin role.
        
        Args:
            user_id: User ID to promote
            
        Returns:
            True if successful
        """
        try:
            user = self.db.query(User).filter_by(id=user_id).first()
            
            if not user:
                self.logger.error(f"User {user_id} not found")
                return False
            
            if user.role == UserRole.ADMIN:
                self.logger.warning(f"User {user_id} is already admin")
                return True
            
            user.role = UserRole.ADMIN
            self.db.commit()
            
            self.logger.info(f"User {user_id} promoted to admin")
            
            # Log audit
            self._log_audit(
                user_id=user_id,
                action="PROMOTE_TO_ADMIN",
                success=True
            )
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Error promoting user: {e}")
            self.db.rollback()
            return False
    
    def ban_user(self, user_id: int, reason: str = None) -> bool:
        """
        Ban a user from the system.
        
        Args:
            user_id: User ID to ban
            reason: Reason for ban
            
        Returns:
            True if successful
        """
        try:
            user = self.db.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False
            
            if user.role == UserRole.ADMIN:
                self.logger.error("Cannot ban admin users")
                return False
            
            # Ban user
            user.role = UserRole.BANNED
            user.is_active = False
            
            # Disable all accounts
            accounts = self.db.query(MT5Account).filter_by(user_id=user_id).all()
            for account in accounts:
                account.auto_trade_enabled = False
                account.status = AccountStatus.INACTIVE
            
            self.db.commit()
            
            self.logger.info(f"User {user_id} banned. Reason: {reason}")
            
            # Log audit
            self._log_audit(
                user_id=user_id,
                action="BAN_USER",
                details=reason,
                success=True
            )
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Error banning user: {e}")
            self.db.rollback()
            return False
    
    def unban_user(self, user_id: int) -> bool:
        """
        Unban a user.
        
        Args:
            user_id: User ID to unban
            
        Returns:
            True if successful
        """
        try:
            user = self.db.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False
            
            user.role = UserRole.USER
            user.is_active = True
            
            self.db.commit()
            
            self.logger.info(f"User {user_id} unbanned")
            
            # Log audit
            self._log_audit(
                user_id=user_id,
                action="UNBAN_USER",
                success=True
            )
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Error unbanning user: {e}")
            self.db.rollback()
            return False
    
    # ==================== SYSTEM ANALYTICS ====================
    
    def get_system_stats(self) -> Dict:
        """
        Get comprehensive system statistics.
        
        Returns:
            Dictionary with system metrics
        """
        try:
            # User stats
            user_stats = self.get_user_stats()
            
            # Account stats
            total_accounts = self.db.query(MT5Account).count()
            active_accounts = self.db.query(MT5Account).filter_by(
                status=AccountStatus.ACTIVE
            ).count()
            auto_trade_accounts = self.db.query(MT5Account).filter_by(
                auto_trade_enabled=True
            ).count()
            
            # Trade stats
            total_trades = self.db.query(Trade).count()
            open_trades = self.db.query(Trade).filter_by(is_closed=False).count()
            closed_trades = self.db.query(Trade).filter_by(is_closed=True).count()
            
            # Performance stats
            winning_trades = self.db.query(Trade).filter(
                Trade.is_closed == True,
                Trade.profit > 0
            ).count()
            
            win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0
            
            # Total P&L
            all_profits = self.db.query(Trade).filter(
                Trade.is_closed == True
            ).all()
            
            total_pnl = sum(t.profit for t in all_profits if t.profit)
            
            # Today's stats
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_trades = self.db.query(Trade).filter(
                Trade.open_time >= today_start
            ).count()
            
            return {
                **user_stats,
                'total_accounts': total_accounts,
                'active_accounts': active_accounts,
                'auto_trade_accounts': auto_trade_accounts,
                'total_trades': total_trades,
                'open_trades': open_trades,
                'closed_trades': closed_trades,
                'winning_trades': winning_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'trades_today': today_trades,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            self.logger.exception(f"Error getting system stats: {e}")
            return {}
    
    def get_top_performers(self, limit: int = 10) -> List[Dict]:
        """
        Get top performing accounts.
        
        Args:
            limit: Number of top performers to return
            
        Returns:
            List of account performance dictionaries
        """
        try:
            accounts = self.db.query(MT5Account).all()
            
            performance_list = []
            
            for account in accounts:
                # Get closed trades for this account
                trades = self.db.query(Trade).filter(
                    Trade.account_id == account.id,
                    Trade.is_closed == True
                ).all()
                
                if not trades:
                    continue
                
                total_pnl = sum(t.profit for t in trades if t.profit)
                total_pips = sum(t.pips for t in trades if t.pips)
                
                winners = len([t for t in trades if t.profit and t.profit > 0])
                win_rate = (winners / len(trades) * 100) if trades else 0
                
                performance_list.append({
                    'account_id': account.id,
                    'account_name': account.account_name,
                    'user_id': account.user_id,
                    'total_pnl': total_pnl,
                    'total_pips': total_pips,
                    'total_trades': len(trades),
                    'win_rate': win_rate
                })
            
            # Sort by total P&L
            performance_list.sort(key=lambda x: x['total_pnl'], reverse=True)
            
            return performance_list[:limit]
            
        except Exception as e:
            self.logger.exception(f"Error getting top performers: {e}")
            return []
    
    # ==================== AUDIT LOGGING ====================
    
    def _log_audit(
        self,
        user_id: int,
        action: str,
        resource_type: str = None,
        resource_id: int = None,
        details: str = None,
        success: bool = True
    ):
        """Log admin action for audit trail."""
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
                success=success,
                timestamp=datetime.utcnow()
            )
            self.db.add(audit_log)
            self.db.commit()
        except Exception as e:
            self.logger.exception(f"Audit logging failed: {e}")
    
    def get_audit_logs(self, limit: int = 100) -> List[AuditLog]:
        """
        Get recent audit logs.
        
        Args:
            limit: Number of logs to retrieve
            
        Returns:
            List of AuditLog objects
        """
        try:
            logs = self.db.query(AuditLog).order_by(
                AuditLog.timestamp.desc()
            ).limit(limit).all()
            
            return logs
            
        except Exception as e:
            self.logger.exception(f"Error getting audit logs: {e}")
            return []
    
    # ==================== HEALTH MONITORING ====================
    
    def get_health_status(self) -> Dict:
        """
        Get system health status.
        
        Returns:
            Dictionary with health metrics
        """
        try:
            # Database health
            db_healthy = True
            try:
                self.db.query(User).first()
            except:
                db_healthy = False
            
            # Get error accounts
            error_accounts = self.db.query(MT5Account).filter_by(
                status=AccountStatus.ERROR
            ).count()
            
            # Get pending accounts
            pending_accounts = self.db.query(MT5Account).filter_by(
                status=AccountStatus.PENDING
            ).count()
            
            # System load (simple check)
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            
            return {
                'database_healthy': db_healthy,
                'error_accounts': error_accounts,
                'pending_accounts': pending_accounts,
                'cpu_usage_percent': cpu_percent,
                'memory_usage_percent': memory_percent,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            self.logger.exception(f"Error getting health status: {e}")
            return {
                'database_healthy': False,
                'error': str(e)
            }


if __name__ == "__main__":
    print("Admin Manager - Production Ready")