import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib
import os
import json
from config import Config
from utils.logger import get_logger

logger = get_logger("ML")

class MLTrainer:
    def __init__(self, db, model_path):
        self.db = db
        self.model_path = model_path
        self.model = None
        self.last_train_count = 0

    def load_model(self):
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                logger.info("Model loaded.")
            except: self.model = None

    def predict(self, signal, df):
        if not self.model: return 0.5
        feats = signal.get('features', {})
        if not feats: return 0.5
        
        X = [[
            feats.get('wick_ratio', 0),
            feats.get('body_ratio', 0),
            feats.get('vol_ratio', 1),
            feats.get('hour', 12),
            feats.get('direction', 1)
        ]]
        return self.model.predict_proba(X)[0][1]

    def retrain_if_needed(self):
        count = self.db.get_trade_count()
        if count >= Config.ML_MIN_TRADES and (count - self.last_train_count) >= Config.ML_RETRAIN_INTERVAL:
            self.train()

    def train(self):
        trades = self.db.get_all_trades()
        if len(trades) < 10: return
        
        data = []
        for t in trades:
            feats = json.loads(t[8])
            if not feats: continue
            
            row = [
                feats.get('wick_ratio', 0),
                feats.get('body_ratio', 0),
                feats.get('vol_ratio', 1),
                feats.get('hour', 12),
                feats.get('direction', 1),
                1 if t[5] > 0 else 0
            ]
            data.append(row)
            
        if len(data) < 10: return
        
        df = pd.DataFrame(data, columns=['wick', 'body', 'vol', 'hour', 'dir', 'target'])
        X = df[['wick', 'body', 'vol', 'hour', 'dir']]
        y = df['target']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
        clf = RandomForestClassifier(n_estimators=100, max_depth=4, random_state=42)
        clf.fit(X_train, y_train)
        
        acc = accuracy_score(y_test, clf.predict(X_test))
        logger.info(f"Model Retrained. Accuracy: {acc:.2f}")
        
        self.model = clf
        joblib.dump(clf, self.model_path)
        self.last_train_count = len(trades)