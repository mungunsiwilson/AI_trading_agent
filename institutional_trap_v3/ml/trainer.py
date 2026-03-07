"""
ml/trainer.py
Machine Learning Trainer for Institutional Trap v3.0
Analyzes past trades to predict win probability of new setups.
"""
import asyncio
import logging
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from execution.trade_database import TradeDatabase

logger = logging.getLogger(__name__)

class MLTrainer:
    def __init__(self, db: TradeDatabase, retrain_threshold: int = 10):
        self.db = db
        self.retrain_threshold = retrain_threshold
        self.model: Optional[Any] = None
        self.is_trained = False
        self.feature_columns = [
            'delta_spike_ratio',      # How strong was the sweep?
            'vwm_distance_pct',       # How far from trend?
            'absorption_bars',        # How long did absorption take?
            'cumulative_delta_norm',  # Net flow during absorption
            'entry_hour',             # Time of day feature
            'day_of_week',            # Day of week feature
            'atr_pct'                 # Volatility context
        ]
        
    def extract_features(self, trade_data: Dict[str, Any]) -> Optional[List[float]]:
        """Extract numerical features from a completed trade record for training."""
        try:
            # Normalize features to prevent scale dominance
            delta_spike = float(trade_data.get('delta_spike_ratio', 0))
            vwm_dist = float(trade_data.get('vwm_distance_pct', 0))
            abs_bars = float(trade_data.get('absorption_bars', 0))
            cum_delta = float(trade_data.get('cumulative_delta_norm', 0))
            
            entry_time = trade_data.get('entry_time')
            if isinstance(entry_time, str):
                entry_dt = datetime.fromisoformat(entry_time)
            else:
                entry_dt = datetime.now() # Fallback
            
            hour = entry_dt.hour
            dow = entry_dt.weekday()
            
            atr_pct = float(trade_data.get('atr_pct', 0))

            return [
                delta_spike,
                vwm_dist,
                abs_bars,
                cum_delta,
                hour,
                dow,
                atr_pct
            ]
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return None

    def prepare_dataset(self) -> Tuple[np.ndarray, np.ndarray]:
        """Load closed trades and prepare X (features) and y (outcome) arrays."""
        trades = self.db.get_all_closed_trades()
        
        if len(trades) < self.retrain_threshold:
            return np.array([]), np.array([])

        X = []
        y = []

        for trade in trades:
            # Only train on trades that have completed feature data
            if not trade.get('delta_spike_ratio'): 
                continue
                
            features = self.extract_features(trade)
            if features:
                X.append(features)
                # Target: 1 if profit > 0, else 0
                outcome = 1 if float(trade.get('pnl', 0)) > 0 else 0
                y.append(outcome)

        if len(X) == 0:
            return np.array([]), np.array([])

        return np.array(X), np.array(y)

    def train(self) -> bool:
        """Train the Random Forest model on historical data."""
        if not SKLEARN_AVAILABLE:
            logger.warning("Scikit-learn not installed. ML disabled.")
            return False

        X, y = self.prepare_dataset()
        
        if len(X) < self.retrain_threshold:
            logger.info(f"Not enough data for ML training. Have {len(X)}, need {self.retrain_threshold}.")
            return False

        try:
            # Split data
            test_size = 0.2 if len(X) > 20 else 0.3
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)

            # Initialize Model (Robust to overfitting with limited data)
            self.model = RandomForestClassifier(
                n_estimators=50,
                max_depth=4,  # Keep shallow to prevent overfitting
                min_samples_split=5,
                random_state=42,
                class_weight='balanced'
            )

            # Train
            self.model.fit(X_train, y_train)

            # Evaluate
            preds = self.model.predict(X_test)
            acc = accuracy_score(y_test, preds)
            
            self.is_trained = True
            logger.info(f"✅ ML Model Retrained. Accuracy: {acc:.2f} on {len(X)} trades.")
            return True

        except Exception as e:
            logger.error(f"ML Training failed: {e}")
            return False

    def predict_probability(self, current_features: Dict[str, Any]) -> float:
        """
        Predict win probability for a potential new trade.
        Returns 0.0 to 1.0.
        """
        if not self.is_trained or self.model is None:
            return 0.5  # Neutral if no model

        features_list = self.extract_features(current_features)
        if not features_list:
            return 0.5

        try:
            # Reshape for sklearn
            X_input = np.array(features_list).reshape(1, -1)
            proba = self.model.predict_proba(X_input)[0][1]  # Probability of class 1 (Win)
            return float(proba)
        except Exception as e:
            logger.error(f"ML Prediction error: {e}")
            return 0.5

    async def auto_retrain_if_needed(self):
        """Check if retraining is needed and perform it."""
        trades_count = len(self.db.get_all_closed_trades())
        
        # Simple logic: if we have new trades since last check, retrain
        # In a real persistent app, we'd store 'last_trained_count' in DB
        if self.is_trained and trades_count <= self.retrain_threshold:
            return # Already trained, not enough new data
            
        if trades_count >= self.retrain_threshold:
            loop = asyncio.get_event_loop()
            # Run blocking sklearn train in executor to not freeze bot
            success = await loop.run_in_executor(None, self.train)
            if success:
                logger.info("ML Model updated with latest trade data.")
