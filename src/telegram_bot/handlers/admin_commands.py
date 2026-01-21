"""Admin Commands - /stats, /users, /broadcast"""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from sqlalchemy.orm import Session
from src.database.models import User, MT5Account, Trade, UserRole

class AdminCommandHandler:
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """System statistics (admin only)."""
        chat_id = update.effective_chat.id
        user = self.db.query(User).filter_by(telegram_chat_id=chat_id).first()
        
        if not user or user.role != UserRole.ADMIN:
            await update.message.reply_text("Admin access required.")
            return
        
        total_users = self.db.query(User).count()
        active_users = self.db.query(User).filter_by(is_active=True).count()
        total_accounts = self.db.query(MT5Account).count()
        active_accounts = self.db.query(MT5Account).filter_by(status='active').count()
        auto_trade_accounts = self.db.query(MT5Account).filter_by(auto_trade_enabled=True).count()
        total_trades = self.db.query(Trade).count()
        open_trades = self.db.query(Trade).filter_by(is_closed=False).count()
        
        stats_msg = f"""
🔧 SYSTEM STATISTICS (ADMIN)

USERS:
Total Users: {total_users}
Active Users: {active_users}

MT5 ACCOUNTS:
Total Accounts: {total_accounts}
Active Accounts: {active_accounts}
Auto-Trade Enabled: {auto_trade_accounts}

TRADING:
Total Trades: {total_trades}
Open Positions: {open_trades}

Bot Status: RUNNING
Version: 2.0.0 Production
        """
        
        await update.message.reply_text(stats_msg.strip())
    
    async def users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all users (admin only)."""
        chat_id = update.effective_chat.id
        user = self.db.query(User).filter_by(telegram_chat_id=chat_id).first()
        
        if not user or user.role != UserRole.ADMIN:
            await update.message.reply_text("Admin access required.")
            return
        
        users = self.db.query(User).order_by(User.created_at.desc()).limit(20).all()
        
        msg = "REGISTERED USERS (Last 20):\n\n"
        
        for u in users:
            msg += f"{'🔴' if not u.is_active else '🟢'} {u.first_name} (@{u.telegram_username or 'N/A'})\n"
            msg += f"   Role: {u.role.value.upper()}\n"
            msg += f"   Chat ID: {u.telegram_chat_id}\n"
            msg += f"   Accounts: {len(u.accounts)}\n\n"
        
        await update.message.reply_text(msg)

def register_admin_handlers(application, db_session: Session):
    handler = AdminCommandHandler(db_session)
    application.add_handler(CommandHandler('stats', handler.stats_command))
    application.add_handler(CommandHandler('users', handler.users_command))