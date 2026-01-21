"""
Telegram Inline Keyboards for User Interface
Author: BLESSING OMOREGIE
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


class BotKeyboards:
    """Telegram bot keyboards and buttons."""
    
    @staticmethod
    def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
        """Main menu keyboard."""
        keyboard = [
            ["My Accounts", "My Trades"],
            ["Enable Auto-Trade", "Disable Auto-Trade"],
            ["Account Stats", "Help"]
        ]
        
        if is_admin:
            keyboard.append(["Admin Panel"])
        
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def account_menu(account_id: int) -> InlineKeyboardMarkup:
        """Account management menu."""
        keyboard = [
            [
                InlineKeyboardButton("Enable Auto-Trade", callback_data=f"enable_auto_{account_id}"),
                InlineKeyboardButton("Disable Auto-Trade", callback_data=f"disable_auto_{account_id}")
            ],
            [
                InlineKeyboardButton("View Stats", callback_data=f"stats_{account_id}"),
                InlineKeyboardButton("Test Connection", callback_data=f"test_{account_id}")
            ],
            [
                InlineKeyboardButton("Edit Settings", callback_data=f"edit_{account_id}"),
                InlineKeyboardButton("Remove Account", callback_data=f"remove_{account_id}")
            ],
            [
                InlineKeyboardButton("Back to Accounts", callback_data="back_accounts")
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def confirm_action(action: str, account_id: int = None) -> InlineKeyboardMarkup:
        """Confirmation keyboard."""
        callback_yes = f"confirm_{action}"
        callback_no = f"cancel_{action}"
        
        if account_id:
            callback_yes += f"_{account_id}"
            callback_no += f"_{account_id}"
        
        keyboard = [
            [
                InlineKeyboardButton("Yes, Confirm", callback_data=callback_yes),
                InlineKeyboardButton("No, Cancel", callback_data=callback_no)
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def admin_menu() -> InlineKeyboardMarkup:
        """Admin panel keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("All Users", callback_data="admin_users"),
                InlineKeyboardButton("System Stats", callback_data="admin_stats")
            ],
            [
                InlineKeyboardButton("Active Trades", callback_data="admin_trades"),
                InlineKeyboardButton("Performance", callback_data="admin_performance")
            ],
            [
                InlineKeyboardButton("Bot Settings", callback_data="admin_settings"),
                InlineKeyboardButton("Broadcast Message", callback_data="admin_broadcast")
            ],
            [
                InlineKeyboardButton("Close", callback_data="admin_close")
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def pagination(current_page: int, total_pages: int, prefix: str) -> InlineKeyboardMarkup:
        """Pagination keyboard."""
        buttons = []
        
        if current_page > 1:
            buttons.append(
                InlineKeyboardButton("Previous", callback_data=f"{prefix}_page_{current_page - 1}")
            )
        
        buttons.append(
            InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop")
        )
        
        if current_page < total_pages:
            buttons.append(
                InlineKeyboardButton("Next", callback_data=f"{prefix}_page_{current_page + 1}")
            )
        
        keyboard = [buttons]
        
        return InlineKeyboardMarkup(keyboard)