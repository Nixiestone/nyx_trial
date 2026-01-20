"""
ML Model Self-Training System
Trains models automatically based on generated signals and actual results

Author: BLESSING OMOREGIE (Enhanced by QDev Team)
Location: src/models/ml_trainer.py (CREATE NEW FILE)
"""

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sqlite3
import json

from ..utils.logger import get_logger


class TrainingDataCollector:
    """Collects training data from signals and actual market results."""
    
    def __init__(self, config, db_path: str = "data/training_data.db"):
        self.config = config
        self.logger = get_logger(__name__, config.LOG_LEVEL, config.LOG_FILE_PATH)
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize training data database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                signal_time TIMESTAMP NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit_1 REAL NOT NULL,
                take_profit_2 REAL NOT NULL,
                scenario TEXT,
                poi_type TEXT,
                confidence REAL,
                ml_prediction_m1 INTEGER,
                ml_prediction_m2 INTEGER,
                ml_prediction_m3 INTEGER,
                ml_prediction_ensemble INTEGER,
                sentiment_score REAL,
                sentiment_label TEXT,
                market_data TEXT,
                actual_outcome INTEGER DEFAULT NULL,
                outcome_time TIMESTAMP DEFAULT NULL,
                outcome_pnl REAL DEFAULT NULL,
                outcome_pips REAL DEFAULT NULL,
                is_trained INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_signal_time ON training_signals(signal_time)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_is_trained ON training_signals(is_trained)
        """)
        
        conn.commit()
        conn.close()
    
    def save_signal(self, signal: Dict, market_data: pd.DataFrame):
        """
        Save signal for future training.
        
        Args:
            signal: Generated trading signal
            market_data: Market data at signal time
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Serialize market data (last 100 candles)
            market_json = market_data.tail(100).to_json()
            
            cursor.execute("""
                INSERT INTO training_signals (
                    symbol, signal_time, direction, entry_price, stop_loss,
                    take_profit_1, take_profit_2, scenario, poi_type, confidence,
                    ml_prediction_m1, ml_prediction_m2, ml_prediction_m3,
                    ml_prediction_ensemble, sentiment_score, sentiment_label,
                    market_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal['symbol'],
                datetime.now(),
                signal['direction'],
                signal['entry_price'],
                signal['stop_loss'],
                signal['take_profit_1'],
                signal['take_profit_2'],
                signal.get('scenario', ''),
                signal.get('poi_type', ''),
                signal['confidence'],
                signal['ml_prediction']['model1'],
                signal['ml_prediction']['model2'],
                signal['ml_prediction']['model3'],
                signal['ml_prediction']['ensemble'],
                signal['sentiment']['score'],
                signal['sentiment']['label'],
                market_json
            ))
            
            conn.commit()
            signal_id = cursor.lastrowid
            conn.close()
            
            self.logger.info(f"Saved signal {signal_id} for future training")
            return signal_id
            
        except Exception as e:
            self.logger.exception(f"Error saving signal: {e}")
            return None
    
    def update_signal_outcome(
        self,
        signal_id: int,
        outcome: int,
        pnl: float = None,
        pips: float = None
    ):
        """
        Update signal with actual outcome.
        
        Args:
            signal_id: Signal database ID
            outcome: -1 (loss), 0 (breakeven), 1 (win)
            pnl: Profit/loss amount
            pips: Pip gain/loss
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE training_signals
                SET actual_outcome = ?, outcome_time = ?, outcome_pnl = ?, outcome_pips = ?
                WHERE id = ?
            """, (outcome, datetime.now(), pnl, pips, signal_id))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Updated signal {signal_id} with outcome: {outcome}")
            
        except Exception as e:
            self.logger.exception(f"Error updating outcome: {e}")
    
    def get_untrained_data(self, min_samples: int = 100) -> Optional[pd.DataFrame]:
        """
        Get signals with outcomes that haven't been used for training.
        
        Args:
            min_samples: Minimum number of samples needed
            
        Returns:
            DataFrame with training data or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            df = pd.read_sql_query("""
                SELECT * FROM training_signals
                WHERE actual_outcome IS NOT NULL
                AND is_trained = 0
                ORDER BY signal_time DESC
            """, conn)
            
            conn.close()
            
            if len(df) < min_samples:
                self.logger.info(f"Not enough training data: {len(df)}/{min_samples}")
                return None
            
            self.logger.info(f"Retrieved {len(df)} samples for training")
            return df
            
        except Exception as e:
            self.logger.exception(f"Error getting training data: {e}")
            return None
    
    def mark_as_trained(self, signal_ids: List[int]):
        """Mark signals as used for training."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(f"""
                UPDATE training_signals
                SET is_trained = 1
                WHERE id IN ({','.join('?' * len(signal_ids))})
            """, signal_ids)
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Marked {len(signal_ids)} signals as trained")
            
        except Exception as e:
            self.logger.exception(f"Error marking as trained: {e}")


class MLModelTrainer:
    """Automatically trains ML models based on collected data."""
    
    def __init__(self, config, ml_ensemble, data_collector: TrainingDataCollector):
        self.config = config
        self.ml_ensemble = ml_ensemble
        self.data_collector = data_collector
        self.logger = get_logger(__name__, config.LOG_LEVEL, config.LOG_FILE_PATH)
        
        self.last_training = None
        self.training_interval_hours = config.ML_RETRAIN_INTERVAL_HOURS
        self.min_samples_required = 100
    
    def should_retrain(self) -> bool:
        """Check if models should be retrained."""
        if self.last_training is None:
            return True
        
        hours_since = (datetime.now() - self.last_training).total_seconds() / 3600
        return hours_since >= self.training_interval_hours
    
    def prepare_training_data(self, df: pd.DataFrame) -> tuple:
        """
        Prepare features and labels from collected signals.
        
        Args:
            df: DataFrame from training_signals table
            
        Returns:
            Tuple of (market_data_df, labels)
        """
        try:
            # Reconstruct market data
            market_data_list = []
            labels = []
            
            for idx, row in df.iterrows():
                # Load market data
                market_json = row['market_data']
                market_df = pd.read_json(market_json)
                
                # Label is the actual outcome
                label = row['actual_outcome']
                
                market_data_list.append(market_df)
                labels.append(label)
            
            # Combine all market data (use first as template)
            if market_data_list:
                combined_df = pd.concat(market_data_list, ignore_index=True)
                labels_array = np.array(labels)
                
                self.logger.info(f"Prepared {len(labels)} training samples")
                return combined_df, labels_array
            
            return None, None
            
        except Exception as e:
            self.logger.exception(f"Error preparing training data: {e}")
            return None, None
    
    def train_models(self) -> bool:
        """
        Train all ML models with collected data.
        
        Returns:
            True if training successful
        """
        try:
            self.logger.info("Starting automatic ML model training...")
            
            # Get untrained data
            df = self.data_collector.get_untrained_data(self.min_samples_required)
            
            if df is None or len(df) < self.min_samples_required:
                self.logger.info(f"Not enough data for training (need {self.min_samples_required})")
                return False
            
            # Prepare training data
            market_data, labels = self.prepare_training_data(df)
            
            if market_data is None or labels is None:
                self.logger.error("Failed to prepare training data")
                return False
            
            # Train ensemble
            self.logger.info(f"Training models with {len(labels)} samples...")
            results = self.ml_ensemble.train_all(market_data, labels)
            
            # Log results
            for model_name, metrics in results.items():
                if 'error' not in metrics:
                    acc_key = 'accuracy' if 'accuracy' in metrics else 'train_accuracy'
                    self.logger.info(f"{model_name}: {metrics.get(acc_key, 0):.4f}")
                else:
                    self.logger.error(f"{model_name} training failed: {metrics['error']}")
            
            # Save models
            self.ml_ensemble.save_all()
            
            # Mark data as trained
            signal_ids = df['id'].tolist()
            self.data_collector.mark_as_trained(signal_ids)
            
            # Update last training time
            self.last_training = datetime.now()
            
            self.logger.info("ML model training completed successfully")
            return True
            
        except Exception as e:
            self.logger.exception(f"Error training models: {e}")
            return False
    
    def auto_train_if_needed(self) -> bool:
        """
        Automatically train if conditions are met.
        
        Returns:
            True if training was performed
        """
        if self.should_retrain():
            return self.train_models()
        return False


if __name__ == "__main__":
    from config.settings import settings
    from src.models.ml_ensemble import MLEnsemble
    
    print("Testing ML Trainer...")
    
    # Initialize components
    collector = TrainingDataCollector(settings)
    ml_ensemble = MLEnsemble(settings)
    trainer = MLModelTrainer(settings, ml_ensemble, collector)
    
    # Test training check
    should_train = trainer.should_retrain()
    print(f"Should retrain: {should_train}")
    
    print("\nML Trainer test completed!")