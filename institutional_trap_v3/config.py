import os
from dotenv import load_dotenv
import MetaTrader5 as mt5

load_dotenv()

class Config:
    # Platform
    PLATFORM = os.getenv("TRADING_PLATFORM", "deriv")
    SYMBOL = os.getenv("SYMBOL", "Volatility 25 Index")
    
    # MT5
    MT5_LOGIN = os.getenv("DERIV_LOGIN")
    MT5_PASSWORD = os.getenv("DERIV_PASSWORD")
    MT5_SERVER = os.getenv("DERIV_SERVER", "Deriv-Demo")
    
    # Telegram
    TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    
    # Timeframes
    TF_1H = mt5.TIMEFRAME_H1
    TF_5M = mt5.TIMEFRAME_M5
    TF_1M = mt5.TIMEFRAME_M1

    # Lookbacks
    LOOKBACK_1H_BARS = 60   # To confirm 1H close
    LOOKBACK_5M_BARS = 12   # To confirm 5M close
    LOOKBACK_1M_BARS = 5    # For pattern confirmation
    
    # Strategy Params
    MIN_BODY_RATIO = float(os.getenv("MIN_BODY_RATIO", "0.70"))
    MIN_WICK_RATIO = float(os.getenv("MIN_WICK_RATIO", "0.60"))

    # Risk
    SL_BUFFER_POINTS = float(os.getenv("SL_BUFFER_POINTS", "15"))
    USE_TRAILING = os.getenv("USE_TRAILING_STOP", "True").lower() == "true"
    TRAIL_ACTIVATION_R = float(os.getenv("TRAILING_ACTIVATION_R", "1.0"))
    TRAIL_DISTANCE_R = float(os.getenv("TRAILING_DISTANCE_R", "0.5"))
    
    # Position
    LOT_SIZE = float(os.getenv("POSITION_SIZE_LOTS", "1.0"))
    
    # ML
    ML_ENABLED = os.getenv("ML_ENABLED", "True").lower() == "true"
    ML_MODEL_PATH = os.getenv("ML_MODEL_PATH", "model.pkl")
    ML_DB_PATH = os.getenv("ML_TRADE_DB", "trades.db")
    ML_RETRAIN_INTERVAL = int(os.getenv("ML_RETRAIN_INTERVAL", "10"))
    ML_MIN_TRADES = int(os.getenv("ML_MIN_TRADES_TO_ACTIVATE", "20"))
    ML_THRESHOLD = float(os.getenv("ML_CONFIDENCE_THRESHOLD", "0.45"))
    
    # Timing (Seconds)
    LEVEL_LOCK_MINUTES = 60

    # entry configs
    MAX_ENTRIES_PER_SETUP = int(os.getenv("MAX_ENTRIES_PER_SETUP", "3"))
    ENTRY_COOLDOWN_SEC = int(os.getenv("ENTRY_COOLDOWN_SEC", "60"))