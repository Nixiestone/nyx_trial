"""
Multi-User Notification System - Production Version
NO EMOJIS - Professional notifications only

Author: BLESSING OMOREGIE (Enhanced by QDev Team)
GitHub: Nixiestone
Repository: nyx_trial

Location: src/notifications/notifier.py (REPLACE EXISTING)
"""

import requests
import json
import sqlite3
from typing import Dict, Optional, List, Set
from datetime import datetime
from pathlib import Path

try:
    from telegram import Bot, Update
    from telegram.ext import Application, CommandHandler, ContextTypes
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

from ..utils.logger import get_logger


class UserDatabase:
    """Manages Telegram user subscriptions."""
    
    def __init__(self, db_path: str = "data/telegram_users.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for users."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                chat_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                active INTEGER DEFAULT 1,
                notifications_enabled INTEGER DEFAULT 1
            )
        """)
        
        conn.commit()
        conn.close()
    
    def add_subscriber(self, chat_id: int, username: str = None, first_name: str = None):
        """Add or update subscriber."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO subscribers (chat_id, username, first_name, active, notifications_enabled)
            VALUES (?, ?, ?, 1, 1)
        """, (chat_id, username, first_name))
        
        conn.commit()
        conn.close()
    
    def remove_subscriber(self, chat_id: int):
        """Remove subscriber (soft delete)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("UPDATE subscribers SET active = 0 WHERE chat_id = ?", (chat_id,))
        
        conn.commit()
        conn.close()
    
    def get_active_subscribers(self) -> List[int]:
        """Get all active subscriber chat IDs."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT chat_id FROM subscribers 
            WHERE active = 1 AND notifications_enabled = 1
        """)
        
        chat_ids = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return chat_ids
    
    def get_subscriber_count(self) -> int:
        """Get total active subscriber count."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM subscribers WHERE active = 1")
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    def is_subscribed(self, chat_id: int) -> bool:
        """Check if user is subscribed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT active FROM subscribers WHERE chat_id = ?
        """, (chat_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None and result[0] == 1


class MultiUserNotifier:
    """
    Multi-user notification system with Telegram bot support.
    NO EMOJIS - Professional trading notifications only.
    """
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger(__name__, config.LOG_LEVEL, config.LOG_FILE_PATH)
        
        # User database
        self.user_db = UserDatabase()
        
        # Initialize Telegram
        self.telegram_bot = None
        self.telegram_app = None
        
        if config.ENABLE_TELEGRAM and TELEGRAM_AVAILABLE:
            if config.TELEGRAM_BOT_TOKEN:
                try:
                    self.telegram_bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
                    self._setup_telegram_bot()
                    self.logger.info("Multi-user Telegram bot initialized")
                except Exception as e:
                    self.logger.error(f"Failed to initialize Telegram: {e}")
        
        # Discord webhook
        self.discord_webhook = config.DISCORD_WEBHOOK_URL if config.ENABLE_DISCORD else None
    
    def _setup_telegram_bot(self):
        """Setup Telegram bot with command handlers."""
        if not TELEGRAM_AVAILABLE or not self.telegram_bot:
            return
        
        try:
            # Create application
            self.telegram_app = Application.builder().token(self.config.TELEGRAM_BOT_TOKEN).build()
            
            # Add command handlers
            self.telegram_app.add_handler(CommandHandler("start", self._cmd_start))
            self.telegram_app.add_handler(CommandHandler("subscribe", self._cmd_subscribe))
            self.telegram_app.add_handler(CommandHandler("unsubscribe", self._cmd_unsubscribe))
            self.telegram_app.add_handler(CommandHandler("status", self._cmd_status))
            self.telegram_app.add_handler(CommandHandler("help", self._cmd_help))
            
            # Start bot in background
            import asyncio
            import threading
            
            def run_bot():
                asyncio.run(self.telegram_app.run_polling())
            
            bot_thread = threading.Thread(target=run_bot, daemon=True)
            bot_thread.start()
            
            self.logger.info("Telegram bot commands registered")
            
        except Exception as e:
            self.logger.error(f"Error setting up Telegram bot: {e}")
    
    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        chat_id = update.effective_chat.id
        username = update.effective_user.username
        first_name = update.effective_user.first_name
        
        # Add user to database
        self.user_db.add_subscriber(chat_id, username, first_name)
        
        welcome_message = f"""
WELCOME TO NYX TRADING BOT

Hello {first_name}!

You have been subscribed to receive professional trading signals and notifications.

AVAILABLE COMMANDS:
/subscribe - Subscribe to notifications
/unsubscribe - Unsubscribe from notifications
/status - Check your subscription status
/help - Show this help message

NOTIFICATION TYPES:
- Trading signals (BUY/SELL setups)
- Trade executions (open/close)
- Daily performance summaries
- Risk alerts
- Bot status updates

You will receive signals based on Smart Money Concepts (SMC) strategy combined with machine learning and sentiment analysis.

Risk Disclaimer: Trading carries risk. Signals are for informational purposes only. Always use proper risk management.

Developed by BLESSING OMOREGIE (Nixiestone)
        """
        
        await update.message.reply_text(welcome_message.strip())
        
        self.logger.info(f"New subscriber: {username} (chat_id: {chat_id})")
    
    async def _cmd_subscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /subscribe command."""
        chat_id = update.effective_chat.id
        username = update.effective_user.username
        first_name = update.effective_user.first_name
        
        self.user_db.add_subscriber(chat_id, username, first_name)
        
        await update.message.reply_text(
            f"Subscription activated for {first_name}!\n\n"
            "You will now receive all trading notifications."
        )
        
        self.logger.info(f"User subscribed: {username} (chat_id: {chat_id})")
    
    async def _cmd_unsubscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unsubscribe command."""
        chat_id = update.effective_chat.id
        
        self.user_db.remove_subscriber(chat_id)
        
        await update.message.reply_text(
            "Unsubscribed successfully.\n\n"
            "You will no longer receive notifications.\n"
            "Use /subscribe to re-enable notifications."
        )
        
        self.logger.info(f"User unsubscribed: chat_id {chat_id}")
    
    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        chat_id = update.effective_chat.id
        is_subscribed = self.user_db.is_subscribed(chat_id)
        total_users = self.user_db.get_subscriber_count()
        
        status = "ACTIVE" if is_subscribed else "INACTIVE"
        
        status_message = f"""
SUBSCRIPTION STATUS

Status: {status}
Total Subscribers: {total_users}

Bot Version: {self.config.APP_VERSION}
Platform: {self.config.PRIMARY_PLATFORM.upper()}
Auto Trading: {'ENABLED' if self.config.AUTO_TRADING_ENABLED else 'DISABLED'}

Use /help for available commands.
        """
        
        await update.message.reply_text(status_message.strip())
    
    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_message = """
NYX TRADING BOT - HELP

COMMANDS:
/start - Get started and subscribe
/subscribe - Enable notifications
/unsubscribe - Disable notifications
/status - Check subscription status
/help - Show this help message

ABOUT:
This bot provides professional trading signals using Smart Money Concepts (SMC), machine learning, and sentiment analysis.

STRATEGY:
- Market structure analysis (MSS/BOS)
- Order blocks and liquidity zones
- Multi-timeframe confirmation
- ML ensemble predictions
- News sentiment analysis

RISK MANAGEMENT:
All signals include:
- Entry price
- Stop loss
- Take profit levels (TP1 and TP2)
- Risk-reward ratios
- Confidence scores

Author: BLESSING OMOREGIE
GitHub: Nixiestone

DISCLAIMER: Trading carries risk. Use proper risk management. Signals are for informational purposes only.
        """
        
        await update.message.reply_text(help_message.strip())
    
    def send_signal_notification(self, signal: Dict):
        """Send trading signal to all subscribers."""
        
        direction_marker = "[BUY]" if signal['direction'] == "BUY" else "[SELL]"
        
        # Calculate pips
        symbol = signal['symbol']
        entry = signal['entry_price']
        current = signal.get('current_price', entry)
        sl = signal['stop_loss']
        tp1 = signal['take_profit_1']
        tp2 = signal['take_profit_2']
        
        # Import symbol normalizer
        from ..utils.symbol_normalizer import SymbolNormalizer
        
        # Get pip value
        pip_value = SymbolNormalizer.get_pip_value(symbol)
        pip_multiplier = 1.0 / pip_value
        
        sl_pips = abs(entry - sl) * pip_multiplier
        tp1_pips = abs(tp1 - entry) * pip_multiplier
        tp2_pips = abs(tp2 - entry) * pip_multiplier
        
        # Get order type info
        order_type = signal.get('order_type', 'Market Order')
        immediate = signal.get('immediate_execution', True)
        order_reason = signal.get('order_reason', 'Price at entry level')
        
        # Order status
        if immediate:
            order_status = "EXECUTE NOW"
            order_marker = "[IMMEDIATE]"
        else:
            order_status = "PENDING ORDER"
            order_marker = "[PENDING]"
        
        message = f"""
{direction_marker} TRADING SIGNAL {order_marker}

Symbol: {symbol}
Direction: {signal['direction']}
Scenario: {signal.get('scenario', 'N/A')}
POI Type: {signal.get('poi_type', 'N/A')}

ORDER TYPE: {order_type}
Status: {order_status}
Reason: {order_reason}

CURRENT PRICE: {current:.5f}
ENTRY PRICE: {entry:.5f}

STOP LOSS: {sl:.5f}
SL Distance: {sl_pips:.1f} pips

TAKE PROFIT 1: {tp1:.5f}
TP1 Distance: {tp1_pips:.1f} pips
R:R TP1: 1:{signal.get('risk_reward_tp1', 0):.2f}

TAKE PROFIT 2: {tp2:.5f}
TP2 Distance: {tp2_pips:.1f} pips
R:R TP2: 1:{signal.get('risk_reward_tp2', 0):.2f}

ANALYSIS:
Confidence: {signal['confidence']*100:.1f}%
ML Prediction: {signal['ml_prediction']['ensemble']} (Conf: {signal['ml_prediction']['confidence']*100:.1f}%)
Sentiment: {signal['sentiment']['label'].upper()} ({signal['sentiment']['score']:.2f})

VALIDATION:
Inducement Swept: {'Yes' if signal.get('inducement_swept', False) else 'No'}
FVG Validation: {'Yes' if signal.get('fvg_validation', False) else 'No'}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

Risk Disclaimer: Use proper risk management. Suggested position size: 1-2% of capital.
        """
        
        self._send_to_all_subscribers(message.strip())
        self._send_discord(message.strip(), "Trading Signal")
    
    def send_trade_execution(self, action: str, details: Dict):
        """Send trade execution notification."""
        
        action_markers = {
            'OPENED': '[TRADE OPENED]',
            'CLOSED': '[TRADE CLOSED]',
            'PARTIAL_CLOSE': '[PARTIAL CLOSE]',
            'MODIFIED': '[TRADE MODIFIED]'
        }
        
        marker = action_markers.get(action, '[TRADE UPDATE]')
        
        message = f"""
{marker}

Symbol: {details.get('symbol', 'N/A')}
Action: {action}
Price: {details.get('price', 'N/A')}
Quantity: {details.get('quantity', 'N/A')} lots
        """
        
        if 'pnl' in details and details['pnl'] != 'N/A':
            pnl = details['pnl']
            pnl_marker = "[PROFIT]" if pnl > 0 else "[LOSS]" if pnl < 0 else "[BREAKEVEN]"
            message += f"\n{pnl_marker} P&L: {pnl:.2f}"
        
        if 'ticket' in details:
            message += f"\nTicket: {details['ticket']}"
        
        message += f"\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        self._send_to_all_subscribers(message.strip())
        self._send_discord(message.strip(), f"Trade {action}")
    
    def send_daily_summary(self, summary: Dict):
        """Send daily performance summary."""
        
        pnl = summary.get('daily_pnl', 0)
        pnl_marker = "[PROFIT DAY]" if pnl > 0 else "[LOSS DAY]" if pnl < 0 else "[BREAKEVEN DAY]"
        
        message = f"""
DAILY PERFORMANCE SUMMARY {pnl_marker}

Date: {datetime.now().strftime('%Y-%m-%d')}

ACCOUNT STATUS:
Balance: {summary.get('balance', 0):.2f}
Equity: {summary.get('equity', 0):.2f}
Daily P&L: {pnl:.2f} ({summary.get('daily_pnl_percent', 0):.2f}%)

TRADING ACTIVITY:
Total Trades: {summary.get('trades_count', 0)}
Winners: {summary.get('winners', 0)}
Losers: {summary.get('losers', 0)}
Win Rate: {summary.get('win_rate', 0):.1f}%

OPEN POSITIONS:
Active Trades: {summary.get('open_positions', 0)}
        """
        
        self._send_to_all_subscribers(message.strip())
        self._send_discord(message.strip(), "Daily Summary")
    
    def send_error_alert(self, error_type: str, message: str):
        """Send error alert notification."""
        
        alert = f"""
[ALERT] ERROR DETECTED

Type: {error_type}
Message: {message}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

Action Required: Please check bot logs for detailed information.
        """
        
        self._send_to_all_subscribers(alert.strip())
        self._send_discord(alert.strip(), "Error Alert")
    
    def send_bot_status(self, status: str, details: Optional[str] = None):
        """Send bot status notification."""
        
        status_markers = {
            'STARTED': '[BOT STARTED]',
            'STOPPED': '[BOT STOPPED]',
            'PAUSED': '[BOT PAUSED]',
            'RESUMED': '[BOT RESUMED]',
            'ERROR': '[BOT ERROR]'
        }
        
        marker = status_markers.get(status, '[BOT STATUS]')
        
        message = f"""
{marker}

Status: {status}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
        """
        
        if details:
            message += f"\n\n{details}"
        
        self._send_to_all_subscribers(message.strip())
        self._send_discord(message.strip(), f"Bot Status: {status}")
    
    def send_pending_order_notification(self, details: Dict):
        """Send pending order notification."""
        
        message = f"""
[PENDING ORDER PLACED]

Symbol: {details.get('symbol', 'N/A')}
Type: {details.get('type', 'N/A')}
Entry Price: {details.get('entry_price', 'N/A')}
Order ID: {details.get('order', 'N/A')}

Status: Waiting for price to reach entry level

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
        """
        
        self._send_to_all_subscribers(message.strip())
    
    def _send_to_all_subscribers(self, message: str):
        """Send message to all active subscribers."""
        
        if not self.config.ENABLE_TELEGRAM or not self.telegram_bot:
            self.logger.debug("Telegram disabled")
            return
        
        subscribers = self.user_db.get_active_subscribers()
        
        if not subscribers:
            self.logger.warning("No active subscribers")
            return
        
        success_count = 0
        fail_count = 0
        
        for chat_id in subscribers:
            try:
                self.telegram_bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=None  # Plain text, no markdown
                )
                success_count += 1
            except Exception as e:
                self.logger.error(f"Failed to send to chat_id {chat_id}: {e}")
                fail_count += 1
        
        self.logger.info(f"Sent to {success_count} subscribers ({fail_count} failures)")
    
    def _send_discord(self, message: str, title: str = "Notification"):
        """Send message via Discord webhook."""
        
        if not self.config.ENABLE_DISCORD or not self.discord_webhook:
            return
        
        try:
            payload = {
                "embeds": [{
                    "title": title,
                    "description": message,
                    "color": 3447003,
                    "timestamp": datetime.utcnow().isoformat()
                }]
            }
            
            response = requests.post(
                self.discord_webhook,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 204:
                self.logger.debug("Discord notification sent")
            else:
                self.logger.error(f"Discord webhook returned {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Failed to send Discord message: {e}")
    
    def test_notifications(self):
        """Test all notification channels."""
        
        test_message = f"""
TEST NOTIFICATION

This is a test message from NYX Trading Bot.

If you receive this, notifications are working correctly.

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

Total Subscribers: {self.user_db.get_subscriber_count()}
        """
        
        self.logger.info("Testing notifications...")
        
        if self.config.ENABLE_TELEGRAM:
            self._send_to_all_subscribers(test_message.strip())
            self.logger.info("Telegram test sent")
        
        if self.config.ENABLE_DISCORD:
            self._send_discord(test_message.strip(), "Test Notification")
            self.logger.info("Discord test sent")
    
    def get_subscriber_count(self) -> int:
        """Get total number of active subscribers."""
        return self.user_db.get_subscriber_count()


if __name__ == "__main__":
    from config.settings import settings
    
    print("Testing Multi-User Notifier...")
    
    notifier = MultiUserNotifier(settings)
    
    print(f"Active subscribers: {notifier.get_subscriber_count()}")
    
    # Test notification
    notifier.test_notifications()
    
    print("\nCheck your Telegram for test message!")
    print("Multi-User Notifier test completed!")