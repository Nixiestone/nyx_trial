from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from sqlalchemy.orm import Session
from src.database.models import User, MT5Account, Trade
from datetime import datetime, timedelta


class MissingCommandHandler:
    """Handles missing commands"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def daily_report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get today's performance report"""
        chat_id = update.effective_chat.id
        user = self.db.query(User).filter_by(telegram_chat_id=chat_id).first()
        
        if not user:
            await update.message.reply_text("User not found.")
            return
        
        # Get today's trades
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        today_trades = self.db.query(Trade).filter(
            Trade.user_id == user.id,
            Trade.open_time >= today_start
        ).all()
        
        if not today_trades:
            await update.message.reply_text(
                f"DAILY REPORT - {datetime.utcnow().strftime('%Y-%m-%d')}\n\n"
                "No trades today.\n\n"
                "Use /mytrades to see all trades."
            )
            return
        
        # Calculate stats
        closed_today = [t for t in today_trades if t.is_closed]
        total_pnl = sum(t.profit for t in closed_today if t.profit)
        total_pips = sum(t.pips for t in closed_today if t.pips)
        
        winners = len([t for t in closed_today if t.profit and t.profit > 0])
        losers = len([t for t in closed_today if t.profit and t.profit < 0])
        
        win_rate = (winners / len(closed_today) * 100) if closed_today else 0
        
        msg = f"DAILY REPORT - {datetime.utcnow().strftime('%Y-%m-%d')}\n\n"
        msg += f"Total Trades: {len(today_trades)}\n"
        msg += f"Closed: {len(closed_today)}\n"
        msg += f"Open: {len(today_trades) - len(closed_today)}\n\n"
        
        if closed_today:
            msg += f"PERFORMANCE:\n"
            msg += f"Winners: {winners}\n"
            msg += f"Losers: {losers}\n"
            msg += f"Win Rate: {win_rate:.1f}%\n\n"
            msg += f"Total P/L: ${total_pnl:.2f}\n"
            msg += f"Total Pips: {total_pips:.1f}\n"
        
        await update.message.reply_text(msg)
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Adjust preferences"""
        await update.message.reply_text(
            "SETTINGS\n\n"
            "This feature is coming soon!\n\n"
            "You'll be able to adjust:\n"
            "- Risk percentage per trade\n"
            "- Maximum daily loss limit\n"
            "- Notification preferences\n"
            "- Trading hours\n\n"
            "For now, use:\n"
            "/notifications - Toggle notifications\n"
            "/autostatus - Check auto-trade status"
        )
    
    async def notifications_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle notifications"""
        chat_id = update.effective_chat.id
        user = self.db.query(User).filter_by(telegram_chat_id=chat_id).first()
        
        if not user:
            await update.message.reply_text("User not found.")
            return
        
        # Toggle
        user.notifications_enabled = not user.notifications_enabled
        self.db.commit()
        
        status = "ENABLED" if user.notifications_enabled else "DISABLED"
        
        await update.message.reply_text(
            f"NOTIFICATIONS {status}\n\n"
            f"You will {'receive' if user.notifications_enabled else 'NOT receive'} notifications for:\n"
            f"- New trading signals\n"
            f"- Trade executions\n"
            f"- Daily reports\n"
            f"- Bot updates\n\n"
            f"Use /notifications again to toggle."
        )
    
    async def risk_settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Risk settings placeholder"""
        await update.message.reply_text(
            "RISK SETTINGS\n\n"
            "This feature is coming soon!\n\n"
            "You'll be able to adjust:\n"
            "- Risk per trade (currently 1%)\n"
            "- Max daily loss (currently 5%)\n"
            "- Max open positions (currently 3)\n"
            "- Position size limits\n\n"
            "Contact https://t.me/Nixiestone for custom risk settings."
        )
    
    async def remove_account_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove account placeholder"""
        await update.message.reply_text(
            "REMOVE ACCOUNT\n\n"
            "This feature is coming soon!\n\n"
            "For now, to remove an account:\n"
            "1. Contact @Nixiestone https://t.me/Nixiestone\n"
            "2. Provide your account login number\n\n"
            "Or use /myaccounts to see your accounts."
        )
    
    async def about_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """About the bot"""
        await update.message.reply_text(
            "ABOUT NYX TRADING BOT\n\n"
            "Version: 2.0.0 Production\n"
            "Developer: BLESSING OMOREGIE\n"
            "Telegram: @Nixiestone\n"
            "GitHub: Nixiestone\n\n"
            "FEATURES:\n"
            "- Smart Money Concepts (SMC) Strategy\n"
            "- Multi-Account Support\n"
            "- Machine Learning Ensemble\n"
            "- Sentiment Analysis\n"
            "- Auto-Trading\n\n"
            "DISCLAIMER:\n"
            "Trading carries risk. Only trade with money you can afford to lose.\n\n"
            "Support: @Nixiestone"
        )


def register_missing_handlers(application, db_session: Session):
    """Register all missing command handlers"""
    handler = MissingCommandHandler(db_session)
    
    application.add_handler(CommandHandler('dailyreport', handler.daily_report_command))
    application.add_handler(CommandHandler('settings', handler.settings_command))
    application.add_handler(CommandHandler('notifications', handler.notifications_command))
    application.add_handler(CommandHandler('risksettings', handler.risk_settings_command))
    application.add_handler(CommandHandler('removeaccount', handler.remove_account_command))
    application.add_handler(CommandHandler('about', handler.about_command))