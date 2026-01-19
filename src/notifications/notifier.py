"""
Notification System - COMPLETE
Author: BLESSING OMOREGIE
GitHub: Nixiestone
Repository: nyx_trial
"""

import requests
from typing import Dict, Optional
from datetime import datetime

try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

from ..utils.logger import get_logger


class Notifier:
    """Send notifications via Telegram, Discord, and Email."""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger(__name__, config.LOG_LEVEL, config.LOG_FILE_PATH)
        
        # Initialize Telegram
        self.telegram_bot = None
        if config.ENABLE_TELEGRAM and TELEGRAM_AVAILABLE:
            if config.TELEGRAM_BOT_TOKEN:
                try:
                    self.telegram_bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
                    self.logger.info("Telegram bot initialized")
                except Exception as e:
                    self.logger.error(f"Failed to initialize Telegram: {e}")
        
        # Discord webhook
        self.discord_webhook = config.DISCORD_WEBHOOK_URL if config.ENABLE_DISCORD else None
    
    def send_signal_notification(self, signal: Dict):
        """Send trading signal notification."""
        
        direction_emoji = "🟢" if signal['direction'] == "BUY" else "🔴"
        
        message = f"""
{direction_emoji} TRADING SIGNAL {direction_emoji}

Symbol: {signal['symbol']}
Direction: {signal['direction']}
Scenario: {signal.get('scenario', 'N/A')}

Entry: {signal['entry_price']:.5f}
Stop Loss: {signal['stop_loss']:.5f}
Take Profit 1: {signal['take_profit_1']:.5f}
Take Profit 2: {signal['take_profit_2']:.5f}

Risk/Reward TP1: {signal.get('risk_reward_tp1', 0):.2f}
Risk/Reward TP2: {signal.get('risk_reward_tp2', 0):.2f}

Confidence: {signal['confidence']*100:.1f}%
ML Prediction: {signal['ml_prediction']['ensemble']}
Sentiment: {signal['sentiment']['label'].upper()}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        self._send_telegram(message.strip())
        self._send_discord(message.strip(), "Trading Signal")
    
    def send_trade_execution(self, action: str, details: Dict):
        """Send trade execution notification."""
        
        emoji_map = {
            'OPENED': '✅',
            'CLOSED': '🔒',
            'PARTIAL_CLOSE': '📊',
            'MODIFIED': '🔧'
        }
        
        emoji = emoji_map.get(action, '📌')
        
        message = f"""
{emoji} TRADE {action} {emoji}

Symbol: {details.get('symbol', 'N/A')}
Price: {details.get('price', 'N/A')}
Quantity: {details.get('quantity', 'N/A')} lots
        """
        
        if 'pnl' in details and details['pnl'] != 'N/A':
            pnl = details['pnl']
            pnl_emoji = "💰" if pnl > 0 else "📉"
            message += f"\n{pnl_emoji} P&L: {pnl:.2f}"
        
        if 'ticket' in details:
            message += f"\nTicket: {details['ticket']}"
        
        message += f"\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        self._send_telegram(message.strip())
        self._send_discord(message.strip(), f"Trade {action}")
    
    def send_daily_summary(self, summary: Dict):
        """Send daily performance summary."""
        
        pnl = summary.get('daily_pnl', 0)
        pnl_emoji = "🎉" if pnl > 0 else "😔" if pnl < 0 else "😐"
        
        message = f"""
📈 DAILY SUMMARY {pnl_emoji}

Date: {datetime.now().strftime('%Y-%m-%d')}

Balance: {summary.get('balance', 0):.2f}
Equity: {summary.get('equity', 0):.2f}
Daily P&L: {pnl:.2f} ({summary.get('daily_pnl_percent', 0):.2f}%)

Trades: {summary.get('trades_count', 0)}
Winners: {summary.get('winners', 0)}
Losers: {summary.get('losers', 0)}
Win Rate: {summary.get('win_rate', 0):.1f}%

Open Positions: {summary.get('open_positions', 0)}
        """
        
        self._send_telegram(message.strip())
        self._send_discord(message.strip(), "Daily Summary")
    
    def send_error_alert(self, error_type: str, message: str):
        """Send error alert notification."""
        
        alert = f"""
⚠️ ERROR ALERT ⚠️

Type: {error_type}
Message: {message}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please check the bot logs for more details.
        """
        
        self._send_telegram(alert.strip())
        self._send_discord(alert.strip(), "Error Alert")
    
    def send_bot_status(self, status: str, details: Optional[str] = None):
        """Send bot status notification."""
        
        emoji_map = {
            'STARTED': '🚀',
            'STOPPED': '🛑',
            'PAUSED': '⏸️',
            'RESUMED': '▶️',
            'ERROR': '❌'
        }
        
        emoji = emoji_map.get(status, '📌')
        
        message = f"""
{emoji} BOT STATUS: {status} {emoji}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        if details:
            message += f"\n\n{details}"
        
        self._send_telegram(message.strip())
        self._send_discord(message.strip(), f"Bot Status: {status}")
    
    def _send_telegram(self, message: str):
        """Send message via Telegram."""
        
        if not self.config.ENABLE_TELEGRAM:
            return
        
        if not self.telegram_bot:
            self.logger.debug("Telegram bot not initialized")
            return
        
        if not self.config.TELEGRAM_CHAT_ID:
            self.logger.error("Telegram chat ID not configured")
            return
        
        try:
            self.telegram_bot.send_message(
                chat_id=self.config.TELEGRAM_CHAT_ID,
                text=message,
                parse_mode='HTML'
            )
            self.logger.debug("Telegram notification sent")
        except Exception as e:
            self.logger.error(f"Failed to send Telegram message: {e}")
    
    def _send_discord(self, message: str, title: str = "Notification"):
        """Send message via Discord webhook."""
        
        if not self.config.ENABLE_DISCORD:
            return
        
        if not self.discord_webhook:
            self.logger.debug("Discord webhook not configured")
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
🧪 TEST NOTIFICATION

This is a test message from NYX Trading Bot.

If you receive this, notifications are working correctly!

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        self.logger.info("Testing notifications...")
        
        if self.config.ENABLE_TELEGRAM:
            self._send_telegram(test_message.strip())
            self.logger.info("Telegram test sent")
        
        if self.config.ENABLE_DISCORD:
            self._send_discord(test_message.strip(), "Test Notification")
            self.logger.info("Discord test sent")


if __name__ == "__main__":
    from config.settings import settings
    
    print("Testing Notifier...")
    
    notifier = Notifier(settings)
    
    # Test notification
    notifier.test_notifications()
    
    print("Check your Telegram/Discord for test message!")
    print("Notifier test completed!")