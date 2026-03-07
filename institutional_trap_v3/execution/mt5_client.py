"""
Deriv MT5 Execution Client
Handles automatic trade execution via MetaTrader 5 on Windows
"""
import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import sys

if sys.platform == "win32":
    import MetaTrader5 as mt5
else:
    mt5 = None  # Mock for non-Windows systems

logger = logging.getLogger(__name__)


class OrderType(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class TradeResult:
    success: bool
    ticket: Optional[int]
    message: str
    price: float = 0.0
    volume: float = 0.0


class DerivMT5Client:
    """
    Async wrapper around MetaTrader5 for Deriv execution
    Provides non-blocking trade execution with retry logic
    """
    
    def __init__(self, config):
        self.config = config
        self.symbol = config.get('SYMBOL', 'R_25')
        self.default_volume = config.get('POSITION_SIZE_USD', 100) / 10000  # Convert to lots
        self.magic_number = config.get('MAGIC_NUMBER', 123456)
        self.deviation_points = config.get('DEVIATION_POINTS', 10)
        self.initialized = False
        self.account_info = None
        
    async def initialize(self) -> bool:
        """Initialize MT5 connection"""
        if sys.platform != "win32":
            logger.error("MT5 only works on Windows")
            return False
            
        try:
            # Initialize MT5
            if not mt5.initialize():
                logger.error(f"MT5 initialization failed: {mt5.last_error()}")
                return False
                
            # Wait for symbol to be ready
            if not mt5.symbol_select(self.symbol, True):
                logger.error(f"Failed to select symbol {self.symbol}")
                return False
                
            self.account_info = mt5.account_info()
            if self.account_info is None:
                logger.error("Failed to get account info")
                return False
                
            self.initialized = True
            logger.info(f"MT5 initialized successfully - Account: {self.account_info.login}, Balance: ${self.account_info.balance:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"MT5 initialization error: {e}")
            return False
    
    def _get_symbol_info(self) -> Optional[Dict]:
        """Get symbol information"""
        if not self.initialized:
            return None
            
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            return None
            
        return {
            'volume_min': symbol_info.volume_min,
            'volume_max': symbol_info.volume_max,
            'volume_step': symbol_info.volume_step,
            'digits': symbol_info.digits,
            'point': symbol_info.point,
            'spread': symbol_info.spread,
            'trade_contract_size': symbol_info.trade_contract_size
        }
    
    def _normalize_volume(self, volume: float) -> float:
        """Normalize volume to symbol requirements"""
        symbol_info = self._get_symbol_info()
        if not symbol_info:
            return self.default_volume
            
        volume = max(symbol_info['volume_min'], min(volume, symbol_info['volume_max']))
        # Round to nearest step
        steps = int(volume / symbol_info['volume_step'])
        return steps * symbol_info['volume_step']
    
    def _get_deviation(self) -> int:
        """Get maximum deviation in points"""
        symbol_info = self._get_symbol_info()
        if not symbol_info:
            return self.deviation_points
        return int(self.deviation_points / symbol_info['point'])
    
    async def execute_market_order(
        self, 
        direction: OrderType, 
        volume: Optional[float] = None,
        comment: str = "InstitutionalTrap_v3"
    ) -> TradeResult:
        """
        Execute a market order asynchronously
        """
        if not self.initialized:
            return TradeResult(False, None, "MT5 not initialized")
        
        try:
            # Run MT5 call in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._execute_market_order_sync,
                direction,
                volume or self.default_volume,
                comment
            )
            return result
            
        except Exception as e:
            logger.error(f"Order execution error: {e}")
            return TradeResult(False, None, f"Execution error: {str(e)}")
    
    def _execute_market_order_sync(
        self,
        direction: OrderType,
        volume: float,
        comment: str
    ) -> TradeResult:
        """Synchronous MT5 order execution"""
        symbol_info = self._get_symbol_info()
        if not symbol_info:
            return TradeResult(False, None, "Symbol info unavailable")
        
        # Normalize volume
        volume = self._normalize_volume(volume)
        
        # Get current price
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return TradeResult(False, None, "No tick data")
        
        price = tick.ask if direction == OrderType.BUY else tick.bid
        sl = 0.0  # Will be set by position manager
        tp = 0.0  # Will be set by position manager
        
        # Prepare order request
        order_type = mt5.ORDER_TYPE_BUY if direction == OrderType.BUY else mt5.ORDER_TYPE_SELL
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": self._get_deviation(),
            "magic": self.magic_number,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Send order
        result = mt5.order_send(request)
        
        if result is None:
            error = mt5.last_error()
            return TradeResult(False, None, f"Order send failed: {error}")
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return TradeResult(False, None, f"Order rejected: {result.comment} (retcode={result.retcode})")
        
        logger.info(f"Order executed: {direction.value} {volume} {self.symbol} @ {price}, Ticket: {result.order}")
        return TradeResult(True, result.order, "Success", price, volume)
    
    async def close_position(self, ticket: int) -> TradeResult:
        """Close a specific position by ticket"""
        if not self.initialized:
            return TradeResult(False, None, "MT5 not initialized")
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._close_position_sync,
                ticket
            )
            return result
            
        except Exception as e:
            logger.error(f"Position close error: {e}")
            return TradeResult(False, None, f"Close error: {str(e)}")
    
    def _close_position_sync(self, ticket: int) -> TradeResult:
        """Synchronous position close"""
        # Get position
        position = mt5.position_get(ticket=ticket)
        if position is None:
            return TradeResult(False, None, f"Position {ticket} not found")
        
        # Determine close order type (opposite of position)
        if position.type == mt5.POSITION_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(self.symbol).bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(self.symbol).ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": self._get_deviation(),
            "magic": self.magic_number,
            "comment": "ClosePosition",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            error = mt5.last_error() if result is None else result.comment
            return TradeResult(False, None, f"Close failed: {error}")
        
        logger.info(f"Position {ticket} closed successfully")
        return TradeResult(True, result.order, "Position closed")
    
    async def get_open_positions(self) -> list:
        """Get all open positions for this symbol"""
        if not self.initialized:
            return []
        
        try:
            loop = asyncio.get_event_loop()
            positions = await loop.run_in_executor(
                None,
                mt5.positions_get,
                self.symbol
            )
            return positions if positions else []
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def get_account_balance(self) -> float:
        """Get current account balance"""
        if not self.initialized:
            return 0.0
        
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, mt5.account_info)
            return info.balance if info else 0.0
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return 0.0
    
    async def shutdown(self):
        """Shutdown MT5 connection"""
        if self.initialized and sys.platform == "win32":
            mt5.shutdown()
            self.initialized = False
            logger.info("MT5 connection closed")


# Mock MT5 for non-Windows testing
class MockMT5:
    """Mock MT5 for testing on non-Windows systems"""
    
    def __init__(self):
        self.initialized = False
        
    def initialize(self):
        self.initialized = True
        return True
    
    def symbol_select(self, symbol, enable):
        return True
    
    def account_info(self):
        class Info:
            login = 12345678
            balance = 10000.0
        return Info()
    
    def symbol_info(self, symbol):
        class SymbolInfo:
            volume_min = 0.01
            volume_max = 100.0
            volume_step = 0.01
            digits = 5
            point = 0.001
            spread = 10
            trade_contract_size = 1.0
        return SymbolInfo()
    
    def symbol_info_tick(self, symbol):
        class Tick:
            ask = 100.0
            bid = 99.9
        return Tick()
    
    def order_send(self, request):
        class Result:
            retcode = 10009  # TRADE_RETCODE_DONE
            order = 12345
            comment = "Done"
        return Result()
    
    def last_error(self):
        return "No error"
    
    def shutdown(self):
        self.initialized = False
    
    def positions_get(self, symbol=None, ticket=None):
        return None
    
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    TRADE_ACTION_DEAL = 1
    ORDER_TIME_GTC = 0
    ORDER_FILLING_IOC = 3
    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1
    TRADE_RETCODE_DONE = 10009


# Replace mt5 with mock on non-Windows
if sys.platform != "win32":
    mt5 = MockMT5()
