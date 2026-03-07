"""
Trade Database and Machine Learning Module
Stores trade history and learns from past performance to optimize strategy parameters
"""
import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """Represents a completed trade"""
    ticket: int
    symbol: str
    direction: str  # BUY or SELL
    entry_price: float
    exit_price: float
    volume: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_percent: float
    stop_loss: float
    take_profit: float
    exit_reason: str  # 'stop_loss', 'take_profit', 'trailing_stop', 'time_limit', 'manual'
    
    # Strategy context at entry
    vwma_1h: float
    atr_1m: float
    delta_spike: float
    absorption_bars: int
    tick_speed_drop: float
    orderbook_depth_change: float
    
    # Outcome label for ML
    outcome: str = None  # 'win', 'loss', 'breakeven'
    
    def __post_init__(self):
        if self.outcome is None:
            if self.pnl > 0:
                self.outcome = 'win'
            elif self.pnl < 0:
                self.outcome = 'loss'
            else:
                self.outcome = 'breakeven'


class TradeDatabase:
    """SQLite database for storing and retrieving trade history"""
    
    def __init__(self, db_path: str = "trades.db"):
        self.db_path = Path(db_path)
        self.conn = None
        self._initialize_db()
    
    def _initialize_db(self):
        """Create database tables"""
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        
        # Trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                ticket INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL NOT NULL,
                volume REAL NOT NULL,
                entry_time TIMESTAMP NOT NULL,
                exit_time TIMESTAMP NOT NULL,
                pnl REAL NOT NULL,
                pnl_percent REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                exit_reason TEXT NOT NULL,
                vwma_1h REAL,
                atr_1m REAL,
                delta_spike REAL,
                absorption_bars INTEGER,
                tick_speed_drop REAL,
                orderbook_depth_change REAL,
                outcome TEXT
            )
        ''')
        
        # Create indexes for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON trades(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entry_time ON trades(entry_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_outcome ON trades(outcome)')
        
        self.conn.commit()
        logger.info(f"Trade database initialized: {self.db_path}")
    
    def save_trade(self, trade: TradeRecord):
        """Save a trade record"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO trades 
            (ticket, symbol, direction, entry_price, exit_price, volume, 
             entry_time, exit_time, pnl, pnl_percent, stop_loss, take_profit,
             exit_reason, vwma_1h, atr_1m, delta_spike, absorption_bars,
             tick_speed_drop, orderbook_depth_change, outcome)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade.ticket, trade.symbol, trade.direction, trade.entry_price,
            trade.exit_price, trade.volume, trade.entry_time.isoformat(),
            trade.exit_time.isoformat(), trade.pnl, trade.pnl_percent,
            trade.stop_loss, trade.take_profit, trade.exit_reason,
            trade.vwma_1h, trade.atr_1m, trade.delta_spike, trade.absorption_bars,
            trade.tick_speed_drop, trade.orderbook_depth_change, trade.outcome
        ))
        self.conn.commit()
        logger.info(f"Trade saved: Ticket {trade.ticket}, PnL: ${trade.pnl:.2f}")
    
    def get_all_trades(self) -> List[TradeRecord]:
        """Retrieve all trades"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM trades ORDER BY entry_time DESC')
        rows = cursor.fetchall()
        return [self._row_to_trade(row) for row in rows]
    
    def get_all_closed_trades(self) -> List[Dict[str, Any]]:
        """Get all completed trades as dictionaries for ML training"""
        trades = self.get_all_trades()
        result = []
        for trade in trades:
            result.append({
                'ticket': trade.ticket,
                'symbol': trade.symbol,
                'direction': trade.direction,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'volume': trade.volume,
                'entry_time': trade.entry_time.isoformat() if trade.entry_time else None,
                'exit_time': trade.exit_time.isoformat() if trade.exit_time else None,
                'pnl': trade.pnl,
                'pnl_percent': trade.pnl_percent,
                'stop_loss': trade.stop_loss,
                'take_profit': trade.take_profit,
                'exit_reason': trade.exit_reason,
                'vwma_1h': trade.vwma_1h,
                'atr_1m': trade.atr_1m,
                'delta_spike_ratio': trade.delta_spike,
                'absorption_bars': trade.absorption_bars,
                'cumulative_delta_norm': trade.tick_speed_drop,  # Reusing field
                'atr_pct': (trade.atr_1m / trade.entry_price * 100) if trade.entry_price > 0 else 0,
                'outcome': trade.outcome
            })
        return result
    
    def get_recent_trades(self, limit: int = 100) -> List[TradeRecord]:
        """Get most recent trades"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM trades ORDER BY entry_time DESC LIMIT ?', (limit,))
        rows = cursor.fetchall()
        return [self._row_to_trade(row) for row in rows]
    
    def get_trades_by_symbol(self, symbol: str) -> List[TradeRecord]:
        """Get trades for a specific symbol"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM trades WHERE symbol = ? ORDER BY entry_time DESC', (symbol,))
        rows = cursor.fetchall()
        return [self._row_to_trade(row) for row in rows]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Calculate overall performance statistics"""
        trades = self.get_all_trades()
        if not trades:
            return {'total_trades': 0}
        
        wins = [t for t in trades if t.outcome == 'win']
        losses = [t for t in trades if t.outcome == 'loss']
        
        total_pnl = sum(t.pnl for t in trades)
        win_rate = len(wins) / len(trades) * 100 if trades else 0
        avg_win = np.mean([t.pnl for t in wins]) if wins else 0
        avg_loss = np.mean([t.pnl for t in losses]) if losses else 0
        profit_factor = abs(sum(t.pnl for t in wins) / sum(t.pnl for t in losses)) if losses and sum(t.pnl for t in losses) != 0 else float('inf')
        
        return {
            'total_trades': len(trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'largest_win': max(t.pnl for t in trades) if trades else 0,
            'largest_loss': min(t.pnl for t in trades) if trades else 0
        }
    
    def _row_to_trade(self, row) -> TradeRecord:
        """Convert database row to TradeRecord"""
        return TradeRecord(
            ticket=row[0], symbol=row[1], direction=row[2],
            entry_price=row[3], exit_price=row[4], volume=row[5],
            entry_time=datetime.fromisoformat(row[6]),
            exit_time=datetime.fromisoformat(row[7]),
            pnl=row[8], pnl_percent=row[9], stop_loss=row[10],
            take_profit=row[11], exit_reason=row[12],
            vwma_1h=row[13], atr_1m=row[14], delta_spike=row[15],
            absorption_bars=row[16], tick_speed_drop=row[17],
            orderbook_depth_change=row[18], outcome=row[19]
        )
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


class StrategyOptimizer:
    """
    Machine Learning module that learns from past trades
    to optimize strategy parameters and improve win rate
    """
    
    def __init__(self, db: TradeDatabase, model_path: str = "ml_model.joblib", min_trades_for_training: int = 20):
        self.db = db
        self.model_path = Path(model_path)
        self.model = None
        self.min_trades_for_training = min_trades_for_training
        self.feature_columns = [
            'vwma_1h', 'atr_1m', 'delta_spike', 'absorption_bars',
            'tick_speed_drop', 'orderbook_depth_change'
        ]
        self.is_trained = False
    
    def prepare_training_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare features and labels from trade history"""
        trades = self.db.get_all_trades()
        
        if len(trades) < self.min_trades_for_training:
            logger.warning(f"Not enough trades for ML ({len(trades)}). Need at least {self.min_trades_for_training}.")
            return None, None
        
        # Convert to DataFrame
        data = []
        for trade in trades:
            data.append({
                'vwma_1h': trade.vwma_1h,
                'atr_1m': trade.atr_1m,
                'delta_spike': trade.delta_spike,
                'absorption_bars': trade.absorption_bars,
                'tick_speed_drop': trade.tick_speed_drop,
                'orderbook_depth_change': trade.orderbook_depth_change,
                'direction_buy': 1 if trade.direction == 'BUY' else 0,
                'outcome': 1 if trade.outcome == 'win' else 0
            })
        
        df = pd.DataFrame(data)
        X = df[self.feature_columns + ['direction_buy']]
        y = df['outcome']
        
        return X, y
    
    def train_model(self) -> bool:
        """Train ML model on historical trades"""
        X, y = self.prepare_training_data()
        
        if X is None or len(X) < self.min_trades_for_training:
            return False
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Train Random Forest classifier
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            min_samples_split=5,
            random_state=42,
            class_weight='balanced'
        )
        
        self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        logger.info(f"Model trained on {len(X)} trades")
        logger.info(f"Test accuracy: {accuracy:.2%}")
        logger.info("\n" + classification_report(y_test, y_pred, target_names=['Loss', 'Win']))
        
        # Save model
        joblib.dump(self.model, self.model_path)
        self.is_trained = True
        
        return True
    
    def load_model(self) -> bool:
        """Load pre-trained model"""
        if self.model_path.exists():
            self.model = joblib.load(self.model_path)
            self.is_trained = True
            logger.info(f"ML model loaded from {self.model_path}")
            return True
        return False
    
    def predict_success_probability(
        self,
        vwma_1h: float,
        atr_1m: float,
        delta_spike: float,
        absorption_bars: int,
        tick_speed_drop: float,
        orderbook_depth_change: float,
        direction: str
    ) -> float:
        """
        Predict probability of trade success based on current conditions
        Returns value between 0.0 and 1.0
        """
        if not self.is_trained:
            return 0.5  # Neutral if no model
        
        try:
            features = np.array([[
                vwma_1h, atr_1m, delta_spike, absorption_bars,
                tick_speed_drop, orderbook_depth_change,
                1 if direction == 'BUY' else 0
            ]])
            
            proba = self.model.predict_proba(features)[0][1]  # Probability of win
            return proba
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return 0.5
    
    def get_optimal_parameters(self) -> Dict[str, Any]:
        """
        Analyze past trades to suggest optimal parameter values
        """
        trades = self.db.get_all_trades()
        
        if len(trades) < 10:
            return {}
        
        wins = [t for t in trades if t.outcome == 'win']
        losses = [t for t in trades if t.outcome == 'loss']
        
        if not wins or not losses:
            return {}
        
        # Calculate average characteristics of winning vs losing trades
        suggestions = {
            'optimal_delta_spike': np.mean([t.delta_spike for t in wins]),
            'optimal_absorption_bars': np.mean([t.absorption_bars for t in wins]),
            'optimal_tick_speed_drop': np.mean([t.tick_speed_drop for t in wins]),
            'optimal_depth_change': np.mean([t.orderbook_depth_change for t in wins]),
            'win_rate_by_direction': {
                'BUY': sum(1 for t in wins if t.direction == 'BUY') / max(1, sum(1 for t in trades if t.direction == 'BUY')),
                'SELL': sum(1 for t in wins if t.direction == 'SELL') / max(1, sum(1 for t in trades if t.direction == 'SELL'))
            }
        }
        
        logger.info("Optimal parameters from historical analysis:")
        for key, value in suggestions.items():
            logger.info(f"  {key}: {value}")
        
        return suggestions
    
    def should_take_trade(
        self,
        features: Dict[str, float],
        min_probability: float = 0.55
    ) -> Tuple[bool, float]:
        """
        Decide whether to take a trade based on ML prediction
        Returns (should_take, probability)
        """
        prob = self.predict_success_probability(
            features.get('vwma_1h', 0),
            features.get('atr_1m', 0),
            features.get('delta_spike', 0),
            features.get('absorption_bars', 0),
            features.get('tick_speed_drop', 0),
            features.get('orderbook_depth_change', 0),
            features.get('direction', 'BUY')
        )
        
        should_take = prob >= min_probability
        logger.info(f"ML Recommendation: {'TAKE' if should_take else 'SKIP'} trade (probability: {prob:.2%})")
        
        return should_take, prob
