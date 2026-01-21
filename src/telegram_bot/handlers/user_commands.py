"""
Telegram Bot User Commands Handler
Handles: /start, /help, /status, /mystats

Author: BLESSING OMOREGIE
"""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from sqlalchemy.orm import Session
from src.database.models import User, UserRole, MT5Account, Trade
from src.telegram_bot.keyboards import BotKeyboards
from src.security.validator import InputValidator
from datetime import datetime, timedelta


class UserCommandHandler:
    """Handles basic user commands."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.validator = InputValidator()
        self.keyboards = BotKeyboards()
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        try:
            chat_id = update.effective_chat.id
            username = update.effective_user.username
            first_name = update.effective_user.first_name
            
            # Validate chat ID
            chat_id = self.validator.validate_telegram_chat_id(chat_id)
            
            # Get or create user
            user = self.db.query(User).filter_by(telegram_chat_id=chat_id).first()
            
            if not user:
                # Create new user
                user = User(
                    telegram_chat_id=chat_id,
                    telegram_username=username,
                    first_name=first_name,
                    role=UserRole.USER,
                    is_active=True,
                    notifications_enabled=True
                )
                self.db.add(user)
                self.db.commit()
                
                welcome_msg = f"""
Welcome to NYX Trading Bot, {first_name}!

PRODUCTION MULTI-USER AUTO-TRADING SYSTEM

You can now:
- Add up to 5 MT5 accounts for auto-trading
- Receive professional trading signals
- Track your performance in real-time
- Enable/disable auto-trading anytime

Get started with /help to see all commands.

IMPORTANT DISCLAIMER:
Trading carries risk. Only use capital you can afford to lose. 
This bot is for informational purposes. Trade responsibly.

Developer: BLESSING OMOREGIE (Nixiestone)
                """
                
                is_admin = False
            else:
                # Existing user
                user.last_active = datetime.utcnow()
                self.db.commit()
                
                welcome_msg = f"""
Welcome back, {first_name}!

NYX Trading Bot is ready.

Use /help to see available commands.
Use /myaccounts to manage your MT5 accounts.
Use /mystats to view your performance.
                """
                
                is_admin = (user.role == UserRole.ADMIN)
            
            # Send welcome message with main menu
            await update.message.reply_text(
                welcome_msg.strip(),
                reply_markup=self.keyboards.main_menu(is_admin=is_admin)
            )
        
        except Exception as e:
            await update.message.reply_text(
                f"Error: {str(e)}\n\nPlease try again or contact support."
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = """
NYX TRADING BOT - COMMAND REFERENCE

ACCOUNT MANAGEMENT:
/addaccount - Add new MT5 account
/myaccounts - View your accounts
/removeaccount - Remove an account
/testconnection - Test account connection

AUTO-TRADING:
/enableautotrade - Enable auto-trading
/disableautotrade - Disable auto-trading
/autostatus - Check auto-trading status

TRADING & PERFORMANCE:
/mytrades - View your trades
/mystats - View performance statistics
/dailyreport - Get today's performance
/positions - View open positions

SETTINGS:
/settings - Adjust your preferences
/notifications - Toggle notifications
/risksettings - Adjust risk parameters

INFORMATION:
/help - Show this help message
/status - Bot and account status
/about - About this bot

Need help? Contact: @Nixiestone
        """
        
        await update.message.reply_text(help_text.strip())
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        try:
            chat_id = update.effective_chat.id
            
            # Get user
            user = self.db.query(User).filter_by(telegram_chat_id=chat_id).first()
            
            if not user:
                await update.message.reply_text("User not found. Please use /start first.")
                return
            
            # Get account stats
            total_accounts = self.db.query(MT5Account).filter_by(user_id=user.id).count()
            active_accounts = self.db.query(MT5Account).filter_by(
                user_id=user.id,
                status='active'
            ).count()
            auto_trade_accounts = self.db.query(MT5Account).filter_by(
                user_id=user.id,
                auto_trade_enabled=True
            ).count()
            
            # Get trade stats
            total_trades = self.db.query(Trade).filter_by(user_id=user.id).count()
            open_trades = self.db.query(Trade).filter_by(
                user_id=user.id,
                is_closed=False
            ).count()
            
            # Today's trades
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_trades = self.db.query(Trade).filter(
                Trade.user_id == user.id,
                Trade.open_time >= today_start
            ).count()
            
            status_msg = f"""
ACCOUNT STATUS

User: {user.first_name} ({user.telegram_username or 'No username'})
Role: {user.role.value.upper()}
Account Status: {'ACTIVE' if user.is_active else 'INACTIVE'}

MT5 ACCOUNTS:
Total Accounts: {total_accounts}/5
Active Accounts: {active_accounts}
Auto-Trade Enabled: {auto_trade_accounts}

TRADING ACTIVITY:
Total Trades: {total_trades}
Open Positions: {open_trades}
Trades Today: {today_trades}

Auto-Trading: {'ENABLED' if user.auto_trade_enabled else 'DISABLED'}
Notifications: {'ON' if user.notifications_enabled else 'OFF'}

Last Active: {user.last_active.strftime('%Y-%m-%d %H:%M UTC') if user.last_active else 'Never'}

Bot Version: 2.0.0 Production
            """
            
            await update.message.reply_text(status_msg.strip())
        
        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")
    
    async def mystats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /mystats command."""
        try:
            chat_id = update.effective_chat.id
            
            user = self.db.query(User).filter_by(telegram_chat_id=chat_id).first()
            if not user:
                await update.message.reply_text("User not found. Please use /start first.")
                return
            
            # Get all trades
            all_trades = self.db.query(Trade).filter_by(user_id=user.id).all()
            
            if not all_trades:
                await update.message.reply_text("No trading history yet. Trades will appear here once executed.")
                return
            
            # Calculate statistics
            closed_trades = [t for t in all_trades if t.is_closed]
            
            total_trades = len(closed_trades)
            winners = len([t for t in closed_trades if t.profit > 0])
            losers = len([t for t in closed_trades if t.profit < 0])
            breakeven = total_trades - winners - losers
            
            win_rate = (winners / total_trades * 100) if total_trades > 0 else 0
            
            total_profit = sum(t.profit for t in closed_trades)
            total_pips = sum(t.pips for t in closed_trades if t.pips)
            
            avg_profit = total_profit / total_trades if total_trades > 0 else 0
            avg_pips = total_pips / total_trades if total_trades > 0 else 0
            
            # Best and worst trades
            if closed_trades:
                best_trade = max(closed_trades, key=lambda t: t.profit)
                worst_trade = min(closed_trades, key=lambda t: t.profit)
            else:
                best_trade = worst_trade = None
            
            # Open positions
            open_positions = [t for t in all_trades if not t.is_closed]
            
            stats_msg = f"""
TRADING PERFORMANCE STATISTICS

OVERALL PERFORMANCE:
Total Trades: {total_trades}
Winners: {winners} ({win_rate:.1f}%)
Losers: {losers} ({100-win_rate:.1f}%)
Breakeven: {breakeven}

PROFIT & LOSS:
Total Profit: ${total_profit:.2f}
Total Pips: {total_pips:.1f}
Average Profit: ${avg_profit:.2f}
Average Pips: {avg_pips:.1f}

BEST TRADE:
{f"{best_trade.symbol} - ${best_trade.profit:.2f}" if best_trade else "N/A"}

WORST TRADE:
{f"{worst_trade.symbol} - ${worst_trade.profit:.2f}" if worst_trade else "N/A"}

CURRENT STATUS:
Open Positions: {len(open_positions)}

Last Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
            """
            
            await update.message.reply_text(stats_msg.strip())
        
        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")


def register_user_handlers(application, db_session: Session):
    """Register all user command handlers."""
    handler = UserCommandHandler(db_session)
    
    application.add_handler(CommandHandler("start", handler.start_command))
    application.add_handler(CommandHandler("help", handler.help_command))
    application.add_handler(CommandHandler("status", handler.status_command))
    application.add_handler(CommandHandler("mystats", handler.mystats_command))