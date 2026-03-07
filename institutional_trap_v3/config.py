"""
Configuration module for Institutional Trap v3.0
Loads environment variables and provides configuration constants.
Supports both Binance Futures and Deriv synthetic indices.
"""

import os
from dotenv import load_dotenv
from typing import Optional, Literal


# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration container with validated settings."""
    
    # Exchange Configuration
    EXCHANGE_API_KEY: str = os.getenv("EXCHANGE_API_KEY", "")
    EXCHANGE_SECRET_KEY: str = os.getenv("EXCHANGE_SECRET_KEY", "")
    EXCHANGE_TESTNET: bool = os.getenv("EXCHANGE_TESTNET", "true").lower() == "true"
    
    # Platform selection: 'binance' or 'deriv'
    TRADING_PLATFORM: Literal["binance", "deriv"] = os.getenv("TRADING_PLATFORM", "binance").lower()
    
    # Trading Configuration
    SYMBOL: str = os.getenv("SYMBOL", "BTC/USDT:USDT")  # For Binance: BTC/USDT:USDT, For Deriv: R_25 (Volatility 25)
    POSITION_SIZE_USD: float = float(os.getenv("POSITION_SIZE_USD", "100"))
    TIME_LIMIT_MINUTES: int = int(os.getenv("TIME_LIMIT_MINUTES", "240"))
    MAX_POSITIONS: int = int(os.getenv("MAX_POSITIONS", "1"))
    TRADING_MODE: str = os.getenv("TRADING_MODE", "BOTH").upper()
    
    # Deriv-specific configuration
    DERIV_APP_ID: str = os.getenv("DERIV_APP_ID", "1089")  # Default is Deriv's public app ID for testing
    DERIV_SERVER: str = os.getenv("DERIV_SERVER", "ws.binaryws.com")  # Production: ws.binaryws.com, Test: ws-test.binaryws.com
    
    # MT5 Configuration (for Windows automation)
    MT5_ENABLED: bool = os.getenv("MT5_ENABLED", "true").lower() == "true"
    MT5_LOGIN: Optional[str] = os.getenv("MT5_LOGIN")  # Optional: auto-login if provided
    MT5_PASSWORD: Optional[str] = os.getenv("MT5_PASSWORD")
    MT5_SERVER: Optional[str] = os.getenv("MT5_SERVER")  # e.g., "Deriv-Demo" or "Deriv-Real"
    MAGIC_NUMBER: int = int(os.getenv("MAGIC_NUMBER", "123456"))
    DEVIATION_POINTS: int = int(os.getenv("DEVIATION_POINTS", "10"))
    
    # Machine Learning Configuration
    ML_ENABLED: bool = os.getenv("ML_ENABLED", "true").lower() == "true"
    ML_MIN_TRADES_FOR_TRAINING: int = int(os.getenv("ML_MIN_TRADES_FOR_TRAINING", "20"))
    ML_MIN_PROBABILITY_THRESHOLD: float = float(os.getenv("ML_MIN_PROBABILITY_THRESHOLD", "0.55"))
    ML_AUTO_RETRAIN: bool = os.getenv("ML_AUTO_RETRAIN", "true").lower() == "true"
    ML_RETRAIN_EVERY_N_TRADES: int = int(os.getenv("ML_RETRAIN_EVERY_N_TRADES", "10"))
    
    # Validation updates for MT5
    @classmethod
    def validate(cls) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if cls.TRADING_PLATFORM == "binance":
            if not cls.EXCHANGE_API_KEY or cls.EXCHANGE_API_KEY == "your_api_key_here":
                errors.append("EXCHANGE_API_KEY not set or using default value")
            
            if not cls.EXCHANGE_SECRET_KEY or cls.EXCHANGE_SECRET_KEY == "your_secret_key_here":
                errors.append("EXCHANGE_SECRET_KEY not set or using default value")
        elif cls.TRADING_PLATFORM == "deriv":
            if not cls.DERIV_APP_ID:
                errors.append("DERIV_APP_ID not set")
            # MT5 is optional for Deriv, but warn if disabled
            if not cls.MT5_ENABLED:
                errors.append("MT5 disabled - trading will be signal-only (no auto-execution)")
        else:
            errors.append("TRADING_PLATFORM must be 'binance' or 'deriv'")
        
        if not cls.TELEGRAM_BOT_TOKEN or cls.TELEGRAM_BOT_TOKEN == "your_bot_token_here":
            errors.append("TELEGRAM_BOT_TOKEN not set or using default value")
        
        if not cls.TELEGRAM_CHAT_ID or cls.TELEGRAM_CHAT_ID == "your_chat_id_here":
            errors.append("TELEGRAM_CHAT_ID not set or using default value")
        
        if cls.POSITION_SIZE_USD <= 0:
            errors.append("POSITION_SIZE_USD must be positive")
        
        if cls.TIME_LIMIT_MINUTES <= 0:
            errors.append("TIME_LIMIT_MINUTES must be positive")
        
        if cls.MAX_POSITIONS < 1:
            errors.append("MAX_POSITIONS must be at least 1")
        
        if cls.TRADING_MODE not in ["BOTH", "LONG_ONLY", "SHORT_ONLY"]:
            errors.append("TRADING_MODE must be BOTH, LONG_ONLY, or SHORT_ONLY")
        
        return errors
    
    @classmethod
    def is_valid(cls) -> bool:
        """Check if configuration is valid."""
        return len(cls.validate()) == 0
    
    @classmethod
    def get_exchange_name(cls) -> str:
        """Get exchange name based on platform."""
        if cls.TRADING_PLATFORM == "deriv":
            return "deriv"
        return "binanceusdm"  # Binance USD-Margined Futures
    
    @classmethod
    def get_symbol_for_ccxt(cls) -> str:
        """Get symbol formatted for CCXT."""
        return cls.SYMBOL
    
    @classmethod
    def get_deriv_symbol(cls) -> str:
        """Get Deriv symbol (e.g., R_25 for Volatility 25)."""
        if cls.TRADING_PLATFORM == "deriv":
            return cls.SYMBOL
        # Default to Volatility 25 if using deriv platform but no symbol set
        return "R_25"
    
    @classmethod
    def get_websocket_url(cls) -> str:
        """Get WebSocket URL based on platform."""
        if cls.TRADING_PLATFORM == "deriv":
            return f"wss://{cls.DERIV_SERVER}/websockets/v3?app_id={cls.DERIV_APP_ID}"
        # Binance Futures
        symbol_lower = cls.SYMBOL.replace("/", "").replace(":USDT", "").lower()
        return f"wss://fstream.binance.com/ws/{symbol_lower}@trade"
