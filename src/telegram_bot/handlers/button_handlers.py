"""
Telegram Button Callback Handlers - NEW FILE
Location: src/telegram_bot/handlers/button_handlers.py (CREATE NEW FILE)

This handles all keyboard button clicks
"""

from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from sqlalchemy.orm import Session
from src.database.models import User, UserRole


class ButtonHandler:
    """Handles all telegram keyboard button callbacks"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def handle_button_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all button clicks"""
        query = update.callback_query
        
        if not query:
            return
        
        await query.answer()
        
        chat_id = update.effective_user.id
        user = self.db.query(User).filter_by(telegram_chat_id=chat_id).first()
        
        if not user:
            await query.edit_message_text("Please use /start first.")
            return
        
        # Route to appropriate handler based on callback data
        data = query.data
        
        # These are handled by other modules
        if data.startswith('enable_auto_') or data.startswith('disable_auto_'):
            return  # Handled by trade_commands
        
        if data.startswith('broadcast_'):
            return  # Handled by admin_commands
        
        # Unhandled callbacks
        await query.edit_message_text(
            f"This feature is coming soon!\n\n"
            f"Use /help to see available commands."
        )


def register_button_handlers(application, db_session: Session):
    """Register button callback handler"""
    handler = ButtonHandler(db_session)
    
    # Catch-all for unhandled callbacks
    application.add_handler(CallbackQueryHandler(
        handler.handle_button_click,
        pattern=".*"  # Catch all
    ))