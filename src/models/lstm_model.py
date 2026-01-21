"""
LSTM Neural Network Model for Price Prediction
PRODUCTION VERSION - With proper error handling

Author: BLESSING OMOREGIE
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple, Dict
import os
import logging

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    tf = None
    keras = None

from ..utils.logger import get_logger


class LSTMModel:
    """
    LSTM model for time series prediction with automatic fallback.
    Returns neutral predictions if TensorFlow is not available.
    """
    
    def __init__(self, config, sequence_length: int = 60):
        """
        Initialize LSTM model.
        
        Args:
            config: Configuration object
            sequence_length: Number of time steps to look back
        """
        self.config = config
        self.logger = get_logger(__name__, config.LOG_LEVEL, config.LOG_FILE_PATH)
        self.sequence_length = sequence_length
        self.model = None
        self.is_trained = False
        self.scaler = None
        
        if not TENSORFLOW_AVAILABLE:
            self.logger.warning(
                "TensorFlow/Keras not available. LSTM model disabled. "
                "Install with: pip install tensorflow==2.13.0"
            )
        else:
            os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
            self.logger.info("LSTM model initialized with TensorFlow")
    
    def _build_model(self, input_shape: tuple) -> Optional['keras.Model']:
        """
        Build LSTM architecture.
        
        Args:
            input_shape: Shape of input data (sequence_length, n_features)
            
        Returns:
            Compiled Keras model or None if TensorFlow unavailable
        """
        if not TENSORFLOW_AVAILABLE:
            return None
        
        model = Sequential([
            LSTM(units=50, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            
            LSTM(units=50, return_sequences=True),
            Dropout(0.2),
            
            LSTM(units=50, return_sequences=False),
            Dropout(0.2),
            
            Dense(units=25, activation='relu'),
            Dropout(0.2),
            
            Dense(units=3, activation='softmax')
        ])
        
        model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def _prepare_sequences(self, df: pd.DataFrame) -> np.ndarray:
        """
        Prepare sequences for LSTM input.
        
        Args:
            df: DataFrame with features
            
        Returns:
            Array of sequences
        """
        sequences = []
        
        for i in range(len(df) - self.sequence_length):
            sequence = df.iloc[i:i + self.sequence_length].values
            sequences.append(sequence)
        
        return np.array(sequences)
    
    def train(
        self, 
        df: pd.DataFrame, 
        labels: np.ndarray, 
        epochs: int = 50, 
        batch_size: int = 32
    ) -> Dict:
        """
        Train LSTM model.
        
        Args:
            df: Training data with features
            labels: Training labels (0=sell, 1=hold, 2=buy)
            epochs: Number of training epochs
            batch_size: Batch size
            
        Returns:
            Dictionary with training metrics
        """
        if not TENSORFLOW_AVAILABLE:
            self.logger.warning("LSTM training skipped - TensorFlow not available")
            return {
                'model': 'lstm',
                'train_accuracy': 0.33,
                'val_accuracy': 0.33,
                'n_samples': 0,
                'status': 'disabled',
                'reason': 'TensorFlow not installed'
            }
        
        try:
            X = self._prepare_sequences(df)
            
            if len(X) == 0:
                self.logger.warning("Not enough data for LSTM training")
                return {
                    'model': 'lstm',
                    'train_accuracy': 0.33,
                    'val_accuracy': 0.33,
                    'n_samples': 0,
                    'status': 'insufficient_data'
                }
            
            y = labels[self.sequence_length:]
            
            y_categorical = keras.utils.to_categorical(y, num_classes=3)
            
            if self.model is None:
                input_shape = (X.shape[1], X.shape[2])
                self.model = self._build_model(input_shape)
            
            callbacks = [
                EarlyStopping(
                    monitor='val_loss',
                    patience=10,
                    restore_best_weights=True
                ),
                ReduceLROnPlateau(
                    monitor='val_loss',
                    factor=0.5,
                    patience=5,
                    min_lr=0.00001
                )
            ]
            
            history = self.model.fit(
                X, y_categorical,
                epochs=epochs,
                batch_size=batch_size,
                validation_split=0.2,
                callbacks=callbacks,
                verbose=0
            )
            
            self.is_trained = True
            
            train_acc = history.history['accuracy'][-1]
            val_acc = history.history['val_accuracy'][-1]
            
            self.logger.info(
                f"LSTM trained - Train Acc: {train_acc:.3f}, Val Acc: {val_acc:.3f}"
            )
            
            return {
                'model': 'lstm',
                'train_accuracy': float(train_acc),
                'val_accuracy': float(val_acc),
                'n_samples': len(X),
                'status': 'success'
            }
            
        except Exception as e:
            self.logger.error(f"LSTM training error: {e}")
            return {
                'model': 'lstm',
                'train_accuracy': 0.33,
                'val_accuracy': 0.33,
                'n_samples': 0,
                'status': 'error',
                'error': str(e)
            }
    
    def predict(self, df: pd.DataFrame) -> Tuple[int, float]:
        """
        Make prediction using LSTM.
        
        Args:
            df: DataFrame with features
            
        Returns:
            Tuple of (prediction, confidence)
            prediction: 0=sell, 1=hold, 2=buy
            confidence: probability of prediction
        """
        if not TENSORFLOW_AVAILABLE or not self.is_trained or self.model is None:
            return 1, 0.33
        
        try:
            X = self._prepare_sequences(df)
            
            if len(X) == 0:
                return 1, 0.33
            
            last_sequence = X[-1].reshape(1, X.shape[1], X.shape[2])
            
            prediction = self.model.predict(last_sequence, verbose=0)
            
            predicted_class = np.argmax(prediction[0])
            confidence = float(prediction[0][predicted_class])
            
            return int(predicted_class), confidence
            
        except Exception as e:
            self.logger.error(f"LSTM prediction error: {e}")
            return 1, 0.33
    
    def save(self, path: Optional[str] = None):
        """
        Save trained model.
        
        Args:
            path: Path to save model. If None, uses default.
        """
        if not TENSORFLOW_AVAILABLE or self.model is None:
            return
        
        try:
            if path is None:
                path = 'models/lstm_model.h5'
            
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self.model.save(path)
            self.logger.info(f"LSTM model saved to {path}")
            
        except Exception as e:
            self.logger.error(f"Error saving LSTM model: {e}")
    
    def load(self, path: Optional[str] = None):
        """
        Load trained model.
        
        Args:
            path: Path to load model from. If None, uses default.
        """
        if not TENSORFLOW_AVAILABLE:
            return
        
        try:
            if path is None:
                path = 'models/lstm_model.h5'
            
            if not os.path.exists(path):
                self.logger.warning(f"LSTM model file not found: {path}")
                return
            
            self.model = keras.models.load_model(path)
            self.is_trained = True
            self.logger.info(f"LSTM model loaded from {path}")
            
        except Exception as e:
            self.logger.error(f"Error loading LSTM model: {e}")


def get_lstm_status() -> Dict:
    """
    Get LSTM model availability status.
    
    Returns:
        Dictionary with status information
    """
    return {
        'available': TENSORFLOW_AVAILABLE,
        'tensorflow_version': tf.__version__ if TENSORFLOW_AVAILABLE else None,
        'keras_version': keras.__version__ if TENSORFLOW_AVAILABLE else None
    }