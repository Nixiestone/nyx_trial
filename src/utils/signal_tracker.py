"""
Signal Deduplication System
Prevents sending the same signal multiple times

Author: BLESSING OMOREGIE (Enhanced by QDev Team)
Location: src/utils/signal_tracker.py (CREATE NEW FILE)
"""

import sqlite3
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple


class SignalTracker:
    """
    Tracks generated signals to prevent duplicates.
    Uses hash-based deduplication with time windows.
    """
    
    def __init__(self, db_path: str = "data/signal_tracker.db", cooldown_hours: int = 24):
        """
        Initialize signal tracker.
        
        Args:
            db_path: Path to SQLite database
            cooldown_hours: Hours before same signal can be sent again
        """
        self.db_path = db_path
        self.cooldown_hours = cooldown_hours
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize signal tracking database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signal_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_hash TEXT NOT NULL UNIQUE,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                scenario TEXT,
                first_seen TIMESTAMP NOT NULL,
                last_seen TIMESTAMP NOT NULL,
                occurrence_count INTEGER DEFAULT 1,
                sent_count INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_signal_hash ON signal_history(signal_hash)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_last_seen ON signal_history(last_seen)
        """)
        
        conn.commit()
        conn.close()
    
    def _generate_signal_hash(self, signal: Dict) -> str:
        """
        Generate unique hash for a signal.
        
        Uses: symbol, direction, entry_price (rounded), scenario, POI type
        
        Args:
            signal: Signal dictionary
            
        Returns:
            SHA256 hash string
        """
        # Round entry price to avoid floating point differences
        entry_rounded = round(signal['entry_price'], 5)
        
        # Create canonical string
        canonical = f"{signal['symbol']}|{signal['direction']}|{entry_rounded}|{signal.get('scenario', '')}|{signal.get('poi_type', '')}"
        
        # Generate hash
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def is_duplicate(self, signal: Dict) -> Tuple[bool, Optional[str]]:
        """
        Check if signal is a duplicate within cooldown period.
        
        Args:
            signal: Signal dictionary
            
        Returns:
            Tuple of (is_duplicate, reason)
        """
        signal_hash = self._generate_signal_hash(signal)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if hash exists and is within cooldown
            cooldown_cutoff = datetime.now() - timedelta(hours=self.cooldown_hours)
            
            cursor.execute("""
                SELECT last_seen, occurrence_count, sent_count
                FROM signal_history
                WHERE signal_hash = ? AND last_seen > ?
            """, (signal_hash, cooldown_cutoff))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                last_seen, occurrence_count, sent_count = result
                last_seen_dt = datetime.fromisoformat(last_seen)
                hours_ago = (datetime.now() - last_seen_dt).total_seconds() / 3600
                
                reason = f"Duplicate signal (last sent {hours_ago:.1f}h ago, occurrence #{occurrence_count})"
                return True, reason
            
            return False, None
            
        except Exception as e:
            # On error, allow signal to be safe
            return False, f"Error checking duplicate: {e}"
    
    def record_signal(self, signal: Dict, was_sent: bool = True):
        """
        Record a signal in the tracking database.
        
        Args:
            signal: Signal dictionary
            was_sent: Whether signal was actually sent to users
        """
        signal_hash = self._generate_signal_hash(signal)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if signal hash exists
            cursor.execute("""
                SELECT id, occurrence_count, sent_count
                FROM signal_history
                WHERE signal_hash = ?
            """, (signal_hash,))
            
            result = cursor.fetchone()
            
            if result:
                # Update existing record
                signal_id, occurrence_count, sent_count = result
                new_occurrence = occurrence_count + 1
                new_sent = sent_count + (1 if was_sent else 0)
                
                cursor.execute("""
                    UPDATE signal_history
                    SET last_seen = ?, occurrence_count = ?, sent_count = ?
                    WHERE id = ?
                """, (datetime.now(), new_occurrence, new_sent, signal_id))
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO signal_history (
                        signal_hash, symbol, direction, entry_price, scenario,
                        first_seen, last_seen, occurrence_count, sent_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    signal_hash,
                    signal['symbol'],
                    signal['direction'],
                    signal['entry_price'],
                    signal.get('scenario', ''),
                    datetime.now(),
                    datetime.now(),
                    1,
                    1 if was_sent else 0
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error recording signal: {e}")
    
    def cleanup_old_signals(self, days: int = 7):
        """
        Remove old signal records to keep database clean.
        
        Args:
            days: Remove signals older than this many days
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor.execute("""
                DELETE FROM signal_history
                WHERE last_seen < ?
            """, (cutoff_date,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                print(f"Cleaned up {deleted_count} old signal records")
            
        except Exception as e:
            print(f"Error cleaning up signals: {e}")
    
    def get_signal_stats(self) -> Dict:
        """
        Get statistics about tracked signals.
        
        Returns:
            Dictionary with statistics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total signals
            cursor.execute("SELECT COUNT(*) FROM signal_history")
            total_signals = cursor.fetchone()[0]
            
            # Signals in last 24 hours
            last_24h = datetime.now() - timedelta(hours=24)
            cursor.execute("""
                SELECT COUNT(*) FROM signal_history
                WHERE last_seen > ?
            """, (last_24h,))
            signals_24h = cursor.fetchone()[0]
            
            # Total occurrences
            cursor.execute("SELECT SUM(occurrence_count) FROM signal_history")
            total_occurrences = cursor.fetchone()[0] or 0
            
            # Total sent
            cursor.execute("SELECT SUM(sent_count) FROM signal_history")
            total_sent = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                'total_unique_signals': total_signals,
                'signals_last_24h': signals_24h,
                'total_occurrences': total_occurrences,
                'total_sent': total_sent,
                'duplicates_prevented': total_occurrences - total_sent
            }
            
        except Exception as e:
            return {'error': str(e)}


if __name__ == "__main__":
    # Test signal tracker
    print("Testing Signal Tracker...")
    
    tracker = SignalTracker(cooldown_hours=24)
    
    # Test signal
    test_signal = {
        'symbol': 'EURUSD',
        'direction': 'BUY',
        'entry_price': 1.10000,
        'scenario': 'Reversal via MSS',
        'poi_type': 'OB'
    }
    
    # First check - should not be duplicate
    is_dup, reason = tracker.is_duplicate(test_signal)
    print(f"\nFirst check: Duplicate = {is_dup}, Reason = {reason}")
    
    # Record signal
    tracker.record_signal(test_signal, was_sent=True)
    print("Signal recorded")
    
    # Second check - should be duplicate
    is_dup, reason = tracker.is_duplicate(test_signal)
    print(f"\nSecond check: Duplicate = {is_dup}, Reason = {reason}")
    
    # Get stats
    stats = tracker.get_signal_stats()
    print(f"\nStats: {stats}")
    
    print("\nSignal Tracker test completed!")