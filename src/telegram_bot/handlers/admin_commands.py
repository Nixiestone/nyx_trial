"""
PRODUCTION-READY Admin Commands Handler
Comprehensive admin functionality with security and audit logging

Author: BLESSING OMOREGIE (Enhanced by Elite QDev Team)
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from sqlalchemy.orm import Session
from src.database.models import User, MT5Account, Trade, UserRole, AuditLog
from src.security.validator import InputValidator, RateLimiter
from datetime import datetime, timedelta
from typing import Dict, List
import json


class AdminCommandHandler:
    """
    Production-ready admin command handler with:
    - Role-based access control
    - Audit logging
    - Rate limiting
    - Input validation
    - Error handling
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.validator = InputValidator()
        self.rate_limiter = RateLimiter(max_calls=50, time_window=60)
    
    def _check_admin(self, chat_id: int) -> tuple[bool, User]:
        """
        Check if user has admin privileges.
        
        Returns:
            Tuple of (is_admin, user_object)
        """
        try:
            user = self.db.query(User).filter_by(telegram_chat_id=chat_id).first()
            
            if not user:
                return False, None
            
            if user.role != UserRole.ADMIN:
                # Log unauthorized access attempt
                self._log_audit(
                    user_id=user.id,
                    action="UNAUTHORIZED_ADMIN_ACCESS",
                    success=False,
                    details="Non-admin user attempted admin command"
                )
                return False, user
            
            return True, user
        except Exception as e:
            return False, None
    
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
            print(f"Audit logging failed: {e}")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Display comprehensive system statistics.
        Admin only. Rate limited.
        """
        chat_id = update.effective_chat.id
        
        # Rate limiting check
        allowed, error = self.rate_limiter.is_allowed(chat_id)
        if not allowed:
            await update.message.reply_text(f"Rate limit exceeded: {error}")
            return
        
        # Admin check
        is_admin, user = self._check_admin(chat_id)
        if not is_admin:
            await update.message.reply_text("Admin access required.")
            return
        
        try:
            # User statistics
            total_users = self.db.query(User).count()
            active_users = self.db.query(User).filter_by(is_active=True).count()
            admin_count = self.db.query(User).filter_by(role=UserRole.ADMIN).count()
            banned_count = self.db.query(User).filter_by(role=UserRole.BANNED).count()
            
            # Account statistics
            total_accounts = self.db.query(MT5Account).count()
            active_accounts = self.db.query(MT5Account).filter_by(status='active').count()
            auto_trade_accounts = self.db.query(MT5Account).filter_by(auto_trade_enabled=True).count()
            pending_accounts = self.db.query(MT5Account).filter_by(status='pending').count()
            error_accounts = self.db.query(MT5Account).filter_by(status='error').count()
            
            # Trading statistics
            total_trades = self.db.query(Trade).count()
            open_trades = self.db.query(Trade).filter_by(is_closed=False).count()
            closed_trades = self.db.query(Trade).filter_by(is_closed=True).count()
            
            # Calculate P&L
            winning_trades = self.db.query(Trade).filter(
                Trade.is_closed == True,
                Trade.profit > 0
            ).count()
            losing_trades = self.db.query(Trade).filter(
                Trade.is_closed == True,
                Trade.profit < 0
            ).count()
            
            win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0
            
            total_profit = self.db.query(Trade).filter(
                Trade.is_closed == True
            ).with_entities(Trade.profit).all()
            total_pnl = sum([t[0] for t in total_profit if t[0] is not None])
            
            # Today's statistics
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_trades = self.db.query(Trade).filter(
                Trade.open_time >= today_start
            ).count()
            
            # System health metrics
            from src.data.mt5_connector import MT5Connector
            from config.settings import settings
            
            mt5_status = "UNKNOWN"
            try:
                connector = MT5Connector(settings)
                if connector.connect():
                    mt5_status = "CONNECTED"
                    connector.disconnect()
                else:
                    mt5_status = "DISCONNECTED"
            except:
                mt5_status = "ERROR"
            
            stats_msg = f"""
SYSTEM STATISTICS - ADMIN PANEL

USER MANAGEMENT:
Total Users: {total_users}
Active Users: {active_users}
Admins: {admin_count}
Banned Users: {banned_count}

MT5 ACCOUNTS:
Total Accounts: {total_accounts}
Active: {active_accounts}
Auto-Trade Enabled: {auto_trade_accounts}
Pending Verification: {pending_accounts}
Error State: {error_accounts}

TRADING ACTIVITY:
Total Trades (All-Time): {total_trades}
Open Positions: {open_trades}
Closed Trades: {closed_trades}
Trades Today: {today_trades}

PERFORMANCE METRICS:
Winning Trades: {winning_trades}
Losing Trades: {losing_trades}
Win Rate: {win_rate:.1f}%
Total P&L: ${total_pnl:.2f}

SYSTEM HEALTH:
MT5 Connection: {mt5_status}
Bot Status: RUNNING
Database: CONNECTED
Version: 2.0.0 Production

Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
            """
            
            # Log admin action
            self._log_audit(
                user_id=user.id,
                action="VIEW_STATS",
                success=True,
                details="Admin viewed system statistics"
            )
            
            await update.message.reply_text(stats_msg.strip())
            
        except Exception as e:
            self._log_audit(
                user_id=user.id if user else None,
                action="VIEW_STATS",
                success=False,
                details=f"Error: {str(e)}"
            )
            await update.message.reply_text(f"Error retrieving statistics: {str(e)}")
    
    async def users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        List all users with pagination and filtering.
        Admin only.
        """
        chat_id = update.effective_chat.id
        
        # Admin check
        is_admin, user = self._check_admin(chat_id)
        if not is_admin:
            await update.message.reply_text("Admin access required.")
            return
        
        try:
            # Get page number from args
            page = 1
            if context.args and context.args[0].isdigit():
                page = int(context.args[0])
            
            page_size = 10
            offset = (page - 1) * page_size
            
            # Get users
            users = self.db.query(User).order_by(
                User.created_at.desc()
            ).offset(offset).limit(page_size).all()
            
            total_users = self.db.query(User).count()
            total_pages = (total_users + page_size - 1) // page_size
            
            if not users:
                await update.message.reply_text("No users found on this page.")
                return
            
            msg = f"REGISTERED USERS (Page {page}/{total_pages})\n\n"
            
            for u in users:
                status_icon = '🟢' if u.is_active else '🔴'
                role_badge = {
                    UserRole.ADMIN: '[ADMIN]',
                    UserRole.USER: '[USER]',
                    UserRole.BANNED: '[BANNED]'
                }.get(u.role, '[UNKNOWN]')
                
                msg += f"{status_icon} {role_badge} {u.first_name}\n"
                msg += f"   Username: @{u.telegram_username or 'N/A'}\n"
                msg += f"   Chat ID: {u.telegram_chat_id}\n"
                msg += f"   Accounts: {len(u.accounts)}\n"
                msg += f"   Registered: {u.created_at.strftime('%Y-%m-%d')}\n"
                msg += f"   Last Active: {u.last_active.strftime('%Y-%m-%d %H:%M') if u.last_active else 'Never'}\n\n"
            
            msg += f"\nTotal Users: {total_users}\n"
            msg += f"Use /users {page + 1} for next page" if page < total_pages else ""
            
            # Log action
            self._log_audit(
                user_id=user.id,
                action="VIEW_USERS",
                success=True,
                details=f"Viewed users page {page}"
            )
            
            await update.message.reply_text(msg)
            
        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")
    
    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Broadcast message to all active users.
        Admin only. Requires confirmation.
        """
        chat_id = update.effective_chat.id
        
        # Admin check
        is_admin, admin_user = self._check_admin(chat_id)
        if not is_admin:
            await update.message.reply_text("Admin access required.")
            return
        
        # Check if message provided
        if not context.args:
            await update.message.reply_text(
                "Usage: /broadcast <message>\n\n"
                "Example: /broadcast System maintenance in 30 minutes"
            )
            return
        
        message = ' '.join(context.args)
        
        # Validate message
        try:
            message = self.validator.sanitize_string(message, max_length=1000)
        except ValueError as e:
            await update.message.reply_text(f"Invalid message: {e}")
            return
        
        # Get user count
        active_users = self.db.query(User).filter_by(
            is_active=True,
            notifications_enabled=True
        ).all()
        
        # Confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm Send", callback_data=f"broadcast_confirm_{chat_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data="broadcast_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Store message in context
        context.user_data['broadcast_message'] = message
        context.user_data['broadcast_count'] = len(active_users)
        
        await update.message.reply_text(
            f"BROADCAST CONFIRMATION\n\n"
            f"Message: {message}\n\n"
            f"Will be sent to: {len(active_users)} active users\n\n"
            f"Are you sure?",
            reply_markup=reply_markup
        )
    
    async def broadcast_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle broadcast confirmation callback."""
        query = update.callback_query
        await query.answer()
        
        chat_id = update.effective_user.id
        
        # Admin check
        is_admin, admin_user = self._check_admin(chat_id)
        if not is_admin:
            await query.edit_message_text("Admin access required.")
            return
        
        if query.data == "broadcast_cancel":
            await query.edit_message_text("Broadcast cancelled.")
            return
        
        if query.data.startswith("broadcast_confirm"):
            message = context.user_data.get('broadcast_message')
            user_count = context.user_data.get('broadcast_count', 0)
            
            if not message:
                await query.edit_message_text("Error: Message not found.")
                return
            
            await query.edit_message_text(
                f"Broadcasting to {user_count} users...\nPlease wait."
            )
            
            # Get all active users
            users = self.db.query(User).filter_by(
                is_active=True,
                notifications_enabled=True
            ).all()
            
            # Send broadcast
            success_count = 0
            fail_count = 0
            
            broadcast_message = f"""
[ADMIN BROADCAST]

{message}

Sent: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
            """
            
            from telegram import Bot
            bot = context.bot
            
            for user in users:
                try:
                    await bot.send_message(
                        chat_id=user.telegram_chat_id,
                        text=broadcast_message.strip()
                    )
                    success_count += 1
                except Exception as e:
                    fail_count += 1
            
            # Log broadcast
            self._log_audit(
                user_id=admin_user.id,
                action="BROADCAST_MESSAGE",
                success=True,
                details=f"Sent to {success_count} users, {fail_count} failed. Message: {message[:100]}"
            )
            
            await query.edit_message_text(
                f"Broadcast complete!\n\n"
                f"Sent: {success_count}\n"
                f"Failed: {fail_count}\n"
                f"Total: {user_count}"
            )
    
    async def ban_user_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Ban a user from the bot.
        Admin only.
        """
        chat_id = update.effective_chat.id
        
        # Admin check
        is_admin, admin_user = self._check_admin(chat_id)
        if not is_admin:
            await update.message.reply_text("Admin access required.")
            return
        
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text(
                "Usage: /banuser <chat_id>\n\n"
                "Use /users to find user chat IDs."
            )
            return
        
        target_chat_id = int(context.args[0])
        
        # Find user
        target_user = self.db.query(User).filter_by(telegram_chat_id=target_chat_id).first()
        
        if not target_user:
            await update.message.reply_text(f"User with chat ID {target_chat_id} not found.")
            return
        
        # Prevent banning admins
        if target_user.role == UserRole.ADMIN:
            await update.message.reply_text("Cannot ban admin users.")
            return
        
        # Ban user
        target_user.role = UserRole.BANNED
        target_user.is_active = False
        
        # Disable all accounts
        for account in target_user.accounts:
            account.auto_trade_enabled = False
            account.status = 'inactive'
        
        self.db.commit()
        
        # Log action
        self._log_audit(
            user_id=admin_user.id,
            action="BAN_USER",
            resource_type="user",
            resource_id=target_user.id,
            success=True,
            details=f"Banned user {target_user.telegram_username} (chat_id: {target_chat_id})"
        )
        
        await update.message.reply_text(
            f"User {target_user.first_name} (@{target_user.telegram_username}) has been banned.\n\n"
            f"All accounts disabled.\n"
            f"Auto-trading stopped."
        )
    
    async def unban_user_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Unban a user. Admin only."""
        chat_id = update.effective_chat.id
        
        is_admin, admin_user = self._check_admin(chat_id)
        if not is_admin:
            await update.message.reply_text("Admin access required.")
            return
        
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text("Usage: /unbanuser <chat_id>")
            return
        
        target_chat_id = int(context.args[0])
        target_user = self.db.query(User).filter_by(telegram_chat_id=target_chat_id).first()
        
        if not target_user:
            await update.message.reply_text(f"User not found.")
            return
        
        target_user.role = UserRole.USER
        target_user.is_active = True
        self.db.commit()
        
        self._log_audit(
            user_id=admin_user.id,
            action="UNBAN_USER",
            resource_type="user",
            resource_id=target_user.id,
            success=True
        )
        
        await update.message.reply_text(f"User {target_user.first_name} has been unbanned.")
    
    async def system_health_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check system health. Admin only."""
        chat_id = update.effective_chat.id
        
        is_admin, admin_user = self._check_admin(chat_id)
        if not is_admin:
            await update.message.reply_text("Admin access required.")
            return
        
        health_msg = "SYSTEM HEALTH CHECK\n\n"
        
        # Database check
        try:
            self.db.query(User).first()
            health_msg += "Database: OK\n"
        except Exception as e:
            health_msg += f"Database: ERROR - {str(e)[:50]}\n"
        
        # MT5 connection check
        from src.data.mt5_connector import MT5Connector
        from config.settings import settings
        
        try:
            connector = MT5Connector(settings)
            if connector.connect():
                health_msg += "MT5 Connection: OK\n"
                connector.disconnect()
            else:
                health_msg += "MT5 Connection: FAILED\n"
        except Exception as e:
            health_msg += f"MT5 Connection: ERROR - {str(e)[:50]}\n"
        
        # Check disk space, memory, etc. (simplified)
        import psutil
        health_msg += f"\nMemory Usage: {psutil.virtual_memory().percent}%\n"
        health_msg += f"CPU Usage: {psutil.cpu_percent()}%\n"
        
        await update.message.reply_text(health_msg)


def register_admin_handlers(application, db_session: Session):
    """Register all admin command handlers."""
    handler = AdminCommandHandler(db_session)
    
    application.add_handler(CommandHandler('stats', handler.stats_command))
    application.add_handler(CommandHandler('users', handler.users_command))
    application.add_handler(CommandHandler('broadcast', handler.broadcast_command))
    application.add_handler(CommandHandler('banuser', handler.ban_user_command))
    application.add_handler(CommandHandler('unbanuser', handler.unban_user_command))
    application.add_handler(CommandHandler('health', handler.system_health_command))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(
        handler.broadcast_callback,
        pattern="^broadcast_"
    ))