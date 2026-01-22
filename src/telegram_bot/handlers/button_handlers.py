"""
Complete Button Handler - ALL KEYBOARDS WORKING
Author: Elite QDev Team

Location: src/telegram_bot/handlers/button_handlers.py (REPLACE)
"""

from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from sqlalchemy.orm import Session
from src.database.models import User, MT5Account, UserRole, AccountStatus
from src.telegram_bot.keyboards import BotKeyboards
from datetime import datetime


class CompleteButtonHandler:
    """Handles ALL telegram keyboard callbacks - PRODUCTION READY."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.keyboards = BotKeyboards()
    
    async def handle_all_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Master callback router."""
        query = update.callback_query
        
        if not query:
            return
        
        await query.answer()
        
        data = query.data
        chat_id = update.effective_user.id
        
        # Get user
        user = self.db.query(User).filter_by(telegram_chat_id=chat_id).first()
        
        if not user:
            await query.edit_message_text("Please use /start first.")
            return
        
        # Route to handlers
        if data.startswith('menu_'):
            await self._handle_menu(query, user, data)
        elif data.startswith('account_'):
            await self._handle_account(query, user, data)
        elif data.startswith('settings_'):
            await self._handle_settings(query, user, data)
        elif data.startswith('admin_'):
            await self._handle_admin(query, user, data)
        elif data.startswith('confirm_') or data.startswith('cancel_'):
            await self._handle_confirmation(query, user, data)
        elif data == 'noop':
            await query.answer("This is just for display")
        else:
            await query.edit_message_text("Unknown action. Use /help")
    
    async def _handle_menu(self, query, user, data):
        """Handle menu navigation."""
        is_admin = (user.role == UserRole.ADMIN)
        
        if data == 'menu_main':
            await query.edit_message_text(
                f"Main Menu\n\nWelcome {user.first_name}!",
                reply_markup=self.keyboards.main_menu(is_admin)
            )
        
        elif data == 'menu_accounts':
            accounts = self.db.query(MT5Account).filter_by(user_id=user.id).all()
            
            if not accounts:
                await query.edit_message_text(
                    "No accounts found.\n\nUse /addaccount to add your first MT5 account.",
                    reply_markup=self.keyboards.close_menu()
                )
            else:
                await query.edit_message_text(
                    "Your MT5 Accounts:",
                    reply_markup=self.keyboards.account_list(accounts)
                )
        
        elif data == 'menu_trades':
            from src.database.models import Trade
            trades = self.db.query(Trade).filter_by(
                user_id=user.id,
                is_closed=False
            ).all()
            
            msg = f"Open Positions: {len(trades)}\n\n"
            msg += "Use /mytrades for full history\n"
            msg += "Use /positions for detailed view"
            
            await query.edit_message_text(
                msg,
                reply_markup=self.keyboards.close_menu()
            )
        
        elif data == 'menu_settings':
            await query.edit_message_text(
                "Settings Menu",
                reply_markup=self.keyboards.settings_menu()
            )
        
        elif data == 'menu_help':
            help_text = """
Help & Commands

/start - Start bot
/help - Show help
/myaccounts - View accounts
/mytrades - View trades
/settings - Settings
            """
            await query.edit_message_text(
                help_text.strip(),
                reply_markup=self.keyboards.close_menu()
            )
        
        elif data == 'menu_admin':
            if user.role == UserRole.ADMIN:
                await query.edit_message_text(
                    "Admin Panel",
                    reply_markup=self.keyboards.admin_menu()
                )
            else:
                await query.edit_message_text("Admin access required.")
        
        elif data == 'menu_close':
            await query.delete_message()
    
    async def _handle_account(self, query, user, data):
        """Handle account actions."""
        
        if data == 'account_add':
            await query.edit_message_text(
                "Use /addaccount to add a new MT5 account.",
                reply_markup=self.keyboards.close_menu()
            )
        
        elif data.startswith('account_view_'):
            account_id = int(data.split('_')[-1])
            account = self.db.query(MT5Account).filter_by(
                id=account_id,
                user_id=user.id
            ).first()
            
            if not account:
                await query.edit_message_text("Account not found.")
                return
            
            msg = f"Account: {account.account_name}\n"
            msg += f"Login: {account.mt5_login}\n"
            msg += f"Status: {account.status.value.upper()}\n"
            msg += f"Auto-Trade: {'ON' if account.auto_trade_enabled else 'OFF'}\n"
            msg += f"Balance: {account.account_balance:.2f} {account.account_currency}\n"
            
            await query.edit_message_text(
                msg,
                reply_markup=self.keyboards.account_detail(
                    account_id,
                    account.auto_trade_enabled
                )
            )
        
        elif data.startswith('account_toggle_auto_'):
            account_id = int(data.split('_')[-1])
            account = self.db.query(MT5Account).filter_by(
                id=account_id,
                user_id=user.id
            ).first()
            
            if account:
                account.auto_trade_enabled = not account.auto_trade_enabled
                self.db.commit()
                
                status = "ENABLED" if account.auto_trade_enabled else "DISABLED"
                await query.answer(f"Auto-trade {status}")
                
                # Refresh view
                msg = f"Account: {account.account_name}\n"
                msg += f"Auto-Trade: {status}\n"
                
                await query.edit_message_text(
                    msg,
                    reply_markup=self.keyboards.account_detail(
                        account_id,
                        account.auto_trade_enabled
                    )
                )
        
        elif data.startswith('account_test_'):
            account_id = int(data.split('_')[-1])
            await query.edit_message_text(
                f"Use /testconnection {account_id} to test MT5 connection.",
                reply_markup=self.keyboards.close_menu()
            )
        
        elif data.startswith('account_stats_'):
            account_id = int(data.split('_')[-1])
            await query.edit_message_text(
                "Use /mystats for detailed statistics.",
                reply_markup=self.keyboards.close_menu()
            )
        
        elif data.startswith('account_risk_'):
            account_id = int(data.split('_')[-1])
            await query.edit_message_text(
                "Use /risksettings to adjust risk parameters.",
                reply_markup=self.keyboards.close_menu()
            )
        
        elif data.startswith('account_remove_'):
            account_id = int(data.split('_')[-1])
            await query.edit_message_text(
                "Use /removeaccount to remove this account.",
                reply_markup=self.keyboards.close_menu()
            )
    
    async def _handle_settings(self, query, user, data):
        """Handle settings actions."""
        
        if data == 'settings_notifications':
            user.notifications_enabled = not user.notifications_enabled
            self.db.commit()
            
            status = "ENABLED" if user.notifications_enabled else "DISABLED"
            await query.answer(f"Notifications {status}")
            
            await query.edit_message_text(
                f"Notifications: {status}",
                reply_markup=self.keyboards.settings_menu()
            )
        
        elif data == 'settings_risk':
            await query.edit_message_text(
                "Use /risksettings to adjust risk parameters.",
                reply_markup=self.keyboards.close_menu()
            )
        
        elif data == 'settings_autotrade':
            await query.edit_message_text(
                "Use /enableautotrade or /disableautotrade",
                reply_markup=self.keyboards.close_menu()
            )
        
        elif data == 'settings_profile':
            msg = f"User Profile\n\n"
            msg += f"Name: {user.first_name}\n"
            msg += f"Username: @{user.telegram_username or 'N/A'}\n"
            msg += f"Role: {user.role.value.upper()}\n"
            msg += f"Registered: {user.created_at.strftime('%Y-%m-%d')}\n"
            
            await query.edit_message_text(
                msg,
                reply_markup=self.keyboards.close_menu()
            )
    
    async def _handle_admin(self, query, user, data):
        """Handle admin actions."""
        
        if user.role != UserRole.ADMIN:
            await query.edit_message_text("Admin access required.")
            return
        
        if data == 'admin_users':
            await query.edit_message_text(
                "Use /users to view all users.",
                reply_markup=self.keyboards.close_menu()
            )
        
        elif data == 'admin_stats':
            await query.edit_message_text(
                "Use /stats for system statistics.",
                reply_markup=self.keyboards.close_menu()
            )
        
        elif data == 'admin_trades':
            await query.edit_message_text(
                "Use /admintrades for active trades.",
                reply_markup=self.keyboards.close_menu()
            )
        
        elif data == 'admin_performance':
            await query.edit_message_text(
                "Use /performance for performance metrics.",
                reply_markup=self.keyboards.close_menu()
            )
        
        elif data == 'admin_broadcast':
            await query.edit_message_text(
                "Use /broadcast <message> to send to all users.",
                reply_markup=self.keyboards.close_menu()
            )
        
        elif data == 'admin_settings':
            await query.edit_message_text(
                "Use /botsettings for bot configuration.",
                reply_markup=self.keyboards.close_menu()
            )
        
        elif data == 'admin_health':
            await query.edit_message_text(
                "Use /health for system health check.",
                reply_markup=self.keyboards.close_menu()
            )
    
    async def _handle_confirmation(self, query, user, data):
        """Handle confirmation dialogs."""
        
        if data.startswith('confirm_'):
            action = data.replace('confirm_', '')
            await query.edit_message_text(f"Action confirmed: {action}")
        
        elif data.startswith('cancel_'):
            await query.edit_message_text("Action cancelled.")


def register_button_handlers(application, db_session: Session):
    """Register the master button handler."""
    handler = CompleteButtonHandler(db_session)
    
    # Single handler for ALL callbacks
    application.add_handler(CallbackQueryHandler(
        handler.handle_all_callbacks
    ))