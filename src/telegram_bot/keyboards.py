"""
Telegram Inline Keyboards 

"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


class BotKeyboards:
    """Production-ready Telegram bot keyboards."""
    
    @staticmethod
    def main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
        """Main menu with inline keyboard (WORKING)."""
        keyboard = [
            [
                InlineKeyboardButton(" My Accounts", callback_data="menu_accounts"),
                InlineKeyboardButton(" My Trades", callback_data="menu_trades")
            ],
            [
                InlineKeyboardButton(" Settings", callback_data="menu_settings"),
                InlineKeyboardButton(" Help", callback_data="menu_help")
            ]
        ]
        
        if is_admin:
            keyboard.append([
                InlineKeyboardButton("🔧 Admin Panel", callback_data="menu_admin")
            ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def account_list(accounts: list) -> InlineKeyboardMarkup:
        """Account selection keyboard."""
        keyboard = []
        
        for idx, account in enumerate(accounts[:10], 1):  # Max 10 accounts
            status_icon = "✅" if account.status.value == "active" else "❌"
            auto_icon = "🟢" if account.auto_trade_enabled else "🔴"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{status_icon}{auto_icon} {idx}. {account.account_name}",
                    callback_data=f"account_view_{account.id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(" Add Account", callback_data="account_add"),
            InlineKeyboardButton("Back", callback_data="menu_main")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def account_detail(account_id: int, auto_enabled: bool) -> InlineKeyboardMarkup:
        """Individual account management keyboard."""
        keyboard = [
            [
                InlineKeyboardButton(
                    f"Auto-Trade: {'ON ' if auto_enabled else 'OFF '}",
                    callback_data=f"account_toggle_auto_{account_id}"
                )
            ],
            [
                InlineKeyboardButton(" Test Connection", callback_data=f"account_test_{account_id}"),
                InlineKeyboardButton("View Stats", callback_data=f"account_stats_{account_id}")
            ],
            [
                InlineKeyboardButton("Risk Settings", callback_data=f"account_risk_{account_id}"),
                InlineKeyboardButton(" Remove", callback_data=f"account_remove_{account_id}")
            ],
            [
                InlineKeyboardButton(" Back to Accounts", callback_data="menu_accounts")
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def confirm_action(action: str, resource_id: int = None) -> InlineKeyboardMarkup:
        """Confirmation keyboard for dangerous actions."""
        callback_yes = f"confirm_{action}"
        callback_no = f"cancel_{action}"
        
        if resource_id:
            callback_yes += f"_{resource_id}"
            callback_no += f"_{resource_id}"
        
        keyboard = [
            [
                InlineKeyboardButton("Yes, Confirm", callback_data=callback_yes),
                InlineKeyboardButton("No, Cancel", callback_data=callback_no)
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def settings_menu() -> InlineKeyboardMarkup:
        """Settings menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("Notifications", callback_data="settings_notifications"),
                InlineKeyboardButton("Risk Settings", callback_data="settings_risk")
            ],
            [
                InlineKeyboardButton(" Auto-Trade", callback_data="settings_autotrade"),
                InlineKeyboardButton(" Profile", callback_data="settings_profile")
            ],
            [
                InlineKeyboardButton("Back", callback_data="menu_main")
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
                InlineKeyboardButton(" Broadcast", callback_data="admin_broadcast"),
                InlineKeyboardButton(" Bot Settings", callback_data="admin_settings")
            ],
            [
                InlineKeyboardButton("System Health", callback_data="admin_health"),
                InlineKeyboardButton("Close", callback_data="menu_main")
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def pagination(current_page: int, total_pages: int, prefix: str) -> InlineKeyboardMarkup:
        """Pagination keyboard."""
        buttons = []
        
        if current_page > 1:
            buttons.append(
                InlineKeyboardButton(" Previous", callback_data=f"{prefix}_page_{current_page - 1}")
            )
        
        buttons.append(
            InlineKeyboardButton(f" {current_page}/{total_pages}", callback_data="noop")
        )
        
        if current_page < total_pages:
            buttons.append(
                InlineKeyboardButton("Next ", callback_data=f"{prefix}_page_{current_page + 1}")
            )
        
        keyboard = [buttons] if buttons else []
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def yes_no(action: str) -> InlineKeyboardMarkup:
        """Simple Yes/No keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("Yes", callback_data=f"yes_{action}"),
                InlineKeyboardButton("No", callback_data=f"no_{action}")
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def close_menu() -> InlineKeyboardMarkup:
        """Single close button."""
        keyboard = [
            [InlineKeyboardButton(" Close", callback_data="menu_close")]
        ]
        
        return InlineKeyboardMarkup(keyboard)


# Quick access functions
def get_main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Quick access to main menu."""
    return BotKeyboards.main_menu(is_admin)


def get_confirmation(action: str, resource_id: int = None) -> InlineKeyboardMarkup:
    """Quick access to confirmation."""
    return BotKeyboards.confirm_action(action, resource_id)


def get_close_button() -> InlineKeyboardMarkup:
    """Quick access to close button."""
    return BotKeyboards.close_menu()


if __name__ == "__main__":
    print("Telegram Keyboards - Production Ready")
    print("All keyboards use proper callback_data patterns")
    print("Callbacks registered in button_handlers.py")