from telegram import Update
from telegram.ext import (
    ContextTypes, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters
)
from sqlalchemy.orm import Session
from src.database.models import User, MT5Account, UserRole, AccountStatus  # FIXED: Added AccountStatus
from src.core.account_manager import AccountManager
from src.telegram_bot.keyboards import BotKeyboards
from src.security.validator import InputValidator

ACCOUNT_NAME, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER = range(4)


class AccountCommandHandler:
    """Handles account management commands - FIXED VERSION"""
    
    def __init__(self, config, db_session: Session):
        self.config = config
        self.db = db_session
        self.validator = InputValidator()
        self.keyboards = BotKeyboards()
        self.account_manager = AccountManager(config, db_session)
    
    async def add_account_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start account addition conversation"""
        try:
            chat_id = update.effective_chat.id
            
            user = self.db.query(User).filter_by(telegram_chat_id=chat_id).first()
            if not user:
                await update.message.reply_text("Please use /start first.")
                return ConversationHandler.END
            
            # FIXED: Use AccountStatus Enum
            existing_count = self.db.query(MT5Account).filter_by(
                user_id=user.id,
                status=AccountStatus.ACTIVE  # ✅ FIXED
            ).count()
            
            max_accounts = 999 if user.role == UserRole.ADMIN else 5
            
            if existing_count >= max_accounts:
                await update.message.reply_text(
                    f"You have reached the maximum of {max_accounts} accounts.\n"
                    "Remove an account first or contact admin."
                )
                return ConversationHandler.END
            
            await update.message.reply_text(
                "Let's add your MT5 account!\n\n"
                "Step 1/4: Enter a friendly name for this account (e.g., 'Main Account', 'Demo 1')\n\n"
                "Send /cancel to abort."
            )
            
            return ACCOUNT_NAME
        
        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")
            return ConversationHandler.END
    
    async def account_name_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process account name"""
        try:
            account_name = self.validator.validate_account_name(update.message.text)
            context.user_data['account_name'] = account_name
            
            await update.message.reply_text(
                f"Great! Account name: {account_name}\n\n"
                "Step 2/4: Enter your MT5 account LOGIN number\n"
                "(This is your account number, usually 6-9 digits)"
            )
            
            return MT5_LOGIN
        
        except ValueError as e:
            await update.message.reply_text(
                f"Invalid account name: {str(e)}\n\n"
                "Please enter a valid account name (3-50 characters, alphanumeric only):"
            )
            return ACCOUNT_NAME
    
    async def mt5_login_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process MT5 login"""
        try:
            mt5_login = self.validator.validate_mt5_login(update.message.text)
            context.user_data['mt5_login'] = mt5_login
            
            await update.message.delete()
            
            await update.effective_chat.send_message(
                f"Login number saved: {mt5_login}\n\n"
                "Step 3/4: Enter your MT5 account PASSWORD\n\n"
                "IMPORTANT: Your password will be encrypted and stored securely.\n"
                "This message will be deleted immediately after processing."
            )
            
            return MT5_PASSWORD
        
        except ValueError as e:
            await update.message.reply_text(
                f"Invalid login: {str(e)}\n\n"
                "Please enter your MT5 login number (numbers only):"
            )
            return MT5_LOGIN
    
    async def mt5_password_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process MT5 password"""
        try:
            password = update.message.text.strip()
            
            if len(password) < 4:
                await update.message.delete()
                await update.effective_chat.send_message(
                    "Password too short. Please enter your MT5 password:"
                )
                return MT5_PASSWORD
            
            context.user_data['mt5_password'] = password
            
            await update.message.delete()
            
            await update.effective_chat.send_message(
                "Password saved securely.\n\n"
                "Step 4/4: Enter your MT5 SERVER name\n"
                "(e.g., 'ICMarkets-Demo', 'Exness-Real', etc.)\n\n"
                "You can find this in your MT5 terminal."
            )
            
            return MT5_SERVER
        
        except Exception as e:
            await update.message.delete()
            await update.effective_chat.send_message(
                f"Error: {str(e)}\n\nPlease enter your password again:"
            )
            return MT5_PASSWORD
    
    async def mt5_server_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process MT5 server and create account"""
        try:
            server = self.validator.sanitize_string(update.message.text, max_length=100)
            
            chat_id = update.effective_chat.id
            user = self.db.query(User).filter_by(telegram_chat_id=chat_id).first()
            
            account_name = context.user_data['account_name']
            mt5_login = context.user_data['mt5_login']
            mt5_password = context.user_data['mt5_password']
            
            await update.message.reply_text(
                "Creating account and testing connection...\n"
                "This may take a few seconds."
            )
            
            account = self.account_manager.add_account(
                user_id=user.id,
                account_name=account_name,
                mt5_login=mt5_login,
                mt5_password=mt5_password,
                mt5_server=server
            )
            
            del context.user_data['mt5_password']
            
            if account and account.status == AccountStatus.ACTIVE:  # FIXED
                await update.message.reply_text(
                    f"SUCCESS! Account added and connection verified.\n\n"
                    f"Account Name: {account_name}\n"
                    f"Login: {mt5_login}\n"
                    f"Server: {server}\n"
                    f"Currency: {account.account_currency}\n"
                    f"Balance: {account.account_balance:.2f}\n"
                    f"Leverage: 1:{account.account_leverage}\n\n"
                    f"Auto-Trading: DISABLED (use /enableautotrade to activate)\n\n"
                    f"Use /myaccounts to manage all your accounts."
                )
            elif account:
                await update.message.reply_text(
                    f"Account created but connection test FAILED.\n\n"
                    f"Error: {account.last_error or 'Unknown error'}\n\n"
                    f"Please verify your credentials and try again.\n"
                    f"Make sure MT5 terminal is running and the server is correct."
                )
            else:
                await update.message.reply_text(
                    "Failed to create account. Please try again or contact support."
                )
            
            return ConversationHandler.END
        
        except Exception as e:
            await update.message.reply_text(
                f"Error creating account: {str(e)}\n\n"
                "Please try /addaccount again."
            )
            return ConversationHandler.END
    
    async def cancel_add_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel account addition"""
        if 'mt5_password' in context.user_data:
            del context.user_data['mt5_password']
        
        await update.message.reply_text(
            "Account addition cancelled.\n\n"
            "Use /addaccount when you're ready to try again."
        )
        return ConversationHandler.END
    
    async def my_accounts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List user's MT5 accounts"""
        try:
            chat_id = update.effective_chat.id
            user = self.db.query(User).filter_by(telegram_chat_id=chat_id).first()
            
            if not user:
                await update.message.reply_text("Please use /start first.")
                return
            
            accounts = self.db.query(MT5Account).filter_by(user_id=user.id).all()
            
            if not accounts:
                await update.message.reply_text(
                    "You don't have any MT5 accounts yet.\n\n"
                    "Use /addaccount to add your first account."
                )
                return
            
            msg = "YOUR MT5 ACCOUNTS:\n\n"
            
            for idx, account in enumerate(accounts, 1):
                status_text = {
                    AccountStatus.ACTIVE: 'ACTIVE',
                    AccountStatus.INACTIVE: 'INACTIVE',
                    AccountStatus.PENDING: 'PENDING',
                    AccountStatus.ERROR: 'ERROR'
                }.get(account.status, 'UNKNOWN')  # FIXED
                
                auto_trade_status = 'ENABLED' if account.auto_trade_enabled else 'DISABLED'
                
                msg += f"{idx}. {account.account_name}\n"
                msg += f"   Login: {account.mt5_login}\n"
                msg += f"   Server: {account.mt5_server}\n"
                msg += f"   Currency: {account.account_currency}\n"
                msg += f"   Balance: {account.account_balance:.2f}\n"
                msg += f"   Auto-Trade: {auto_trade_status}\n"
                msg += f"   Status: {status_text}\n"
                msg += f"   Last Connected: {account.last_connected.strftime('%Y-%m-%d %H:%M') if account.last_connected else 'Never'}\n"
                
                if account.status == AccountStatus.ERROR:  # FIXED
                    msg += f"   Error: {account.last_error[:50]}...\n"
                
                msg += "\n"
            
            msg += "Use /testconnection <account_number> to test connection\n"
            msg += "Use /removeaccount <account_number> to remove an account"
            
            await update.message.reply_text(msg)
        
        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")
    
    async def test_connection_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Test MT5 connection for an account - FIXED"""
        try:
            chat_id = update.effective_chat.id
            user = self.db.query(User).filter_by(telegram_chat_id=chat_id).first()
            
            if not user:
                await update.message.reply_text("Please use /start first.")
                return
            
            # FIXED: Validate input properly
            if not context.args:
                await update.message.reply_text(
                    "Usage: /testconnection <account_number>\n\n"
                    "Example: /testconnection 1\n\n"
                    "Use /myaccounts to see your account numbers."
                )
                return
            
            # FIXED: Better error handling
            try:
                account_number = int(context.args[0])
            except ValueError:
                await update.message.reply_text(
                    "Invalid account number. Please use a number.\n\n"
                    "Example: /testconnection 1\n\n"
                    "Use /myaccounts to see your accounts."
                )
                return
            
            # FIXED: Get accounts and validate index
            accounts = self.db.query(MT5Account).filter_by(user_id=user.id).all()
            
            if not accounts:
                await update.message.reply_text("You don't have any accounts. Use /addaccount to add one.")
                return
            
            # FIXED: Proper bounds checking
            if account_number < 1 or account_number > len(accounts):
                await update.message.reply_text(
                    f"Invalid account number. You have {len(accounts)} account(s).\n\n"
                    f"Valid numbers: 1 to {len(accounts)}\n\n"
                    "Use /myaccounts to see your accounts."
                )
                return
            
            # FIXED: Correct indexing (user enters 1-based, array is 0-based)
            account = accounts[account_number - 1]
            
            await update.message.reply_text(
                f"Testing connection to {account.account_name}...\n"
                "Please wait..."
            )
            
            success = self.account_manager.test_connection(account.id)
            
            if success:
                self.db.refresh(account)
                
                await update.message.reply_text(
                    f"CONNECTION SUCCESSFUL\n\n"
                    f"Account: {account.account_name}\n"
                    f"Login: {account.mt5_login}\n"
                    f"Server: {account.mt5_server}\n"
                    f"Currency: {account.account_currency}\n"
                    f"Balance: {account.account_balance:.2f}\n"
                    f"Equity: {account.account_equity:.2f}\n"
                    f"Leverage: 1:{account.account_leverage}\n"
                    f"Status: ACTIVE"
                )
            else:
                await update.message.reply_text(
                    f"CONNECTION FAILED\n\n"
                    f"Account: {account.account_name}\n"
                    f"Login: {account.mt5_login}\n"
                    f"Server: {account.mt5_server}\n\n"
                    f"Possible reasons:\n"
                    f"- MT5 terminal not running\n"
                    f"- Wrong server name\n"
                    f"- Network issues\n"
                    f"- Invalid credentials\n\n"
                    f"Please check and try again."
                )
        
        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")


def register_account_handlers(application, db_session: Session):
    """Register all account management handlers"""
    from config.settings import settings
    
    handler = AccountCommandHandler(settings, db_session)
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('addaccount', handler.add_account_start)],
        states={
            ACCOUNT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handler.account_name_received)],
            MT5_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handler.mt5_login_received)],
            MT5_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handler.mt5_password_received)],
            MT5_SERVER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handler.mt5_server_received)],
        },
        fallbacks=[CommandHandler('cancel', handler.cancel_add_account)]
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('myaccounts', handler.my_accounts_command))
    application.add_handler(CommandHandler('testconnection', handler.test_connection_command))