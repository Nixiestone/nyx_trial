"""Trade Management Commands - /enableautotrade, /disableautotrade, /mytrades"""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from sqlalchemy.orm import Session
from src.database.models import User, MT5Account, Trade

class TradeCommandHandler:
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def enable_autotrade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enable auto-trading for all user accounts."""
        chat_id = update.effective_chat.id
        user = self.db.query(User).filter_by(telegram_chat_id=chat_id).first()
        
        if not user:
            await update.message.reply_text("Use /start first.")
            return
        
        accounts = self.db.query(MT5Account).filter_by(user_id=user.id, status='active').all()
        
        if not accounts:
            await update.message.reply_text("No active accounts. Add one with /addaccount")
            return
        
        for account in accounts:
            account.auto_trade_enabled = True
        
        self.db.commit()
        
        await update.message.reply_text(
            f"✅ Auto-trading ENABLED for {len(accounts)} account(s).\n\n"
            "You will now receive and execute signals automatically."
        )
    
    async def disable_autotrade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Disable auto-trading."""
        chat_id = update.effective_chat.id
        user = self.db.query(User).filter_by(telegram_chat_id=chat_id).first()
        
        if not user:
            return
        
        accounts = self.db.query(MT5Account).filter_by(user_id=user.id).all()
        
        for account in accounts:
            account.auto_trade_enabled = False
        
        self.db.commit()
        
        await update.message.reply_text(
            "🔴 Auto-trading DISABLED for all accounts.\n\n"
            "You will still receive signal notifications."
        )
    
    async def my_trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's trades."""
        chat_id = update.effective_chat.id
        user = self.db.query(User).filter_by(telegram_chat_id=chat_id).first()
        
        if not user:
            return
        
        trades = self.db.query(Trade).filter_by(user_id=user.id).order_by(Trade.open_time.desc()).limit(10).all()
        
        if not trades:
            await update.message.reply_text("No trades yet.")
            return
        
        msg = "YOUR RECENT TRADES (Last 10):\n\n"
        
        for trade in trades:
            status = "🟢 OPEN" if not trade.is_closed else "🔴 CLOSED"
            pnl_emoji = "💰" if trade.profit > 0 else "📉" if trade.profit < 0 else "➖"
            
            msg += f"{status} {trade.symbol} {trade.direction}\n"
            msg += f"Entry: {trade.entry_price:.5f}\n"
            
            if trade.is_closed:
                msg += f"{pnl_emoji} P/L: ${trade.profit:.2f}\n"
            
            msg += "\n"
        
        await update.message.reply_text(msg)

def register_trade_handlers(application, db_session: Session):
    handler = TradeCommandHandler(db_session)
    application.add_handler(CommandHandler('enableautotrade', handler.enable_autotrade))
    application.add_handler(CommandHandler('disableautotrade', handler.disable_autotrade))
    application.add_handler(CommandHandler('mytrades', handler.my_trades))