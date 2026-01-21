"""
Offline Message Queue System - NEW FILE
Location: src/telegram_bot/message_queue.py (CREATE NEW FILE)

Queues messages when bot is offline and sends them when back online
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from telegram import Bot


class MessageQueue:
    """Manages message queue for offline delivery"""
    
    def __init__(self, db_path: str = "data/message_queue.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize message queue database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                message_text TEXT NOT NULL,
                message_type TEXT DEFAULT 'text',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                attempts INTEGER DEFAULT 0,
                sent INTEGER DEFAULT 0,
                error TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sent ON message_queue(sent)
        """)
        
        conn.commit()
        conn.close()
    
    def queue_message(self, chat_id: int, message_text: str, message_type: str = 'text'):
        """
        Add message to queue.
        
        Args:
            chat_id: Telegram chat ID
            message_text: Message content
            message_type: Type of message (text, signal, report)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO message_queue (chat_id, message_text, message_type)
                VALUES (?, ?, ?)
            """, (chat_id, message_text, message_type))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error queueing message: {e}")
    
    async def send_queued_messages(self, bot: Bot) -> Dict[str, int]:
        """
        Send all queued messages.
        
        Args:
            bot: Telegram Bot instance
            
        Returns:
            Dictionary with stats
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all unsent messages
        cursor.execute("""
            SELECT id, chat_id, message_text, message_type, attempts
            FROM message_queue
            WHERE sent = 0 AND attempts < 3
            ORDER BY created_at ASC
        """)
        
        messages = cursor.fetchall()
        conn.close()
        
        sent_count = 0
        failed_count = 0
        
        for msg_id, chat_id, text, msg_type, attempts in messages:
            try:
                # Send message
                await bot.send_message(
                    chat_id=chat_id,
                    text=text
                )
                
                # Mark as sent
                self._mark_sent(msg_id)
                sent_count += 1
                
            except Exception as e:
                # Update attempts and error
                self._update_failure(msg_id, str(e))
                failed_count += 1
        
        return {
            'sent': sent_count,
            'failed': failed_count,
            'total': len(messages)
        }
    
    def _mark_sent(self, message_id: int):
        """Mark message as sent"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE message_queue
                SET sent = 1
                WHERE id = ?
            """, (message_id,))
            
            conn.commit()
            conn.close()
        except:
            pass
    
    def _update_failure(self, message_id: int, error: str):
        """Update failed attempt"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE message_queue
                SET attempts = attempts + 1, error = ?
                WHERE id = ?
            """, (error[:500], message_id))
            
            conn.commit()
            conn.close()
        except:
            pass
    
    def cleanup_old_messages(self, days: int = 7):
        """Remove old sent messages"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM message_queue
                WHERE sent = 1
                AND created_at < datetime('now', '-' || ? || ' days')
            """, (days,))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            return deleted
        except:
            return 0
    
    def get_queue_stats(self) -> Dict:
        """Get queue statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM message_queue WHERE sent = 0")
            pending = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM message_queue WHERE sent = 1")
            sent = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM message_queue WHERE attempts >= 3 AND sent = 0")
            failed = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'pending': pending,
                'sent': sent,
                'failed': failed
            }
        except:
            return {'pending': 0, 'sent': 0, 'failed': 0}


# Global instance
_message_queue = None


def get_message_queue() -> MessageQueue:
    """Get or create message queue instance"""
    global _message_queue
    if _message_queue is None:
        _message_queue = MessageQueue()
    return _message_queue