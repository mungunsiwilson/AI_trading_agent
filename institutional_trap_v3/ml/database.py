import sqlite3
import json
from config import Config

class TradeDatabase:
    def __init__(self):
        self.conn = None

    def init_db(self):
        self.conn = sqlite3.connect(Config.ML_DB_PATH, check_same_thread=False)
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                direction TEXT,
                entry_price REAL,
                exit_price REAL,
                profit REAL,
                reason TEXT,
                duration_min REAL,
                features_json TEXT
            )
        ''')
        self.conn.commit()

    def save_trade(self, direction, entry_price, exit_price, profit, reason, duration, features=None):
        cursor = self.conn.cursor()
        feat_str = json.dumps(features) if features else '{}'
        cursor.execute('''
            INSERT INTO trades (direction, entry_price, exit_price, profit, reason, duration_min, features_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (direction, entry_price, exit_price, profit, reason, duration, feat_str))
        self.conn.commit()

    def get_all_trades(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM trades")
        return cursor.fetchall()
        
    def get_trade_count(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM trades")
        return cursor.fetchone()[0]

    def close(self):
        if self.conn: self.conn.close()