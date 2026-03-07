"""
Efficient circular buffers for real-time data.
Uses collections.deque with maxlen for O(1) append operations.
Maintains running sums where possible for efficient rolling calculations.
"""

from collections import deque
from typing import Optional, List, Tuple
import numpy as np


class CircularBuffer:
    """
    Thread-safe circular buffer using deque.
    Optimized for rolling window operations.
    """
    
    def __init__(self, maxlen: int):
        """
        Initialize circular buffer.
        
        Args:
            maxlen: Maximum number of elements to keep
        """
        self._buffer: deque = deque(maxlen=maxlen)
        self.maxlen = maxlen
    
    def append(self, value: float) -> None:
        """Append value to buffer."""
        self._buffer.append(value)
    
    def extend(self, values: List[float]) -> None:
        """Extend buffer with multiple values."""
        self._buffer.extend(values)
    
    def get_all(self) -> List[float]:
        """Get all values as list."""
        return list(self._buffer)
    
    def get_array(self) -> np.ndarray:
        """Get all values as numpy array for vectorized operations."""
        return np.array(self._buffer, dtype=np.float64)
    
    def get_recent(self, n: int) -> List[float]:
        """Get last n values."""
        if n >= len(self._buffer):
            return list(self._buffer)
        return list(self._buffer)[-n:]
    
    def __len__(self) -> int:
        return len(self._buffer)
    
    def __getitem__(self, idx: int) -> float:
        return self._buffer[idx]
    
    def is_full(self) -> bool:
        """Check if buffer is at max capacity."""
        return len(self._buffer) == self.maxlen
    
    def clear(self) -> None:
        """Clear all values."""
        self._buffer.clear()


class RollingSum:
    """
    Efficient rolling sum calculator.
    Maintains running sum to avoid O(n) recalculation.
    """
    
    def __init__(self, period: int):
        """
        Initialize rolling sum calculator.
        
        Args:
            period: Window size for rolling sum
        """
        self.period = period
        self._buffer: deque = deque(maxlen=period)
        self._running_sum: float = 0.0
    
    def update(self, value: float) -> float:
        """
        Update with new value and return current rolling sum.
        
        Args:
            value: New value to add
        
        Returns:
            Current rolling sum
        """
        if len(self._buffer) == self.period:
            # Remove oldest value from sum
            old_value = self._buffer[0]
            self._running_sum -= old_value
        
        self._buffer.append(value)
        self._running_sum += value
        
        return self._running_sum
    
    def get_sum(self) -> float:
        """Get current rolling sum."""
        return self._running_sum
    
    def get_average(self) -> float:
        """Get current rolling average."""
        if len(self._buffer) == 0:
            return 0.0
        return self._running_sum / len(self._buffer)
    
    def __len__(self) -> int:
        return len(self._buffer)
    
    def is_full(self) -> bool:
        """Check if buffer is at full period."""
        return len(self._buffer) == self.period
    
    def clear(self) -> None:
        """Clear all values."""
        self._buffer.clear()
        self._running_sum = 0.0


class OrderBookDepth:
    """
    Efficient order book depth tracker.
    Tracks top N levels of bids and asks with fast updates.
    """
    
    def __init__(self, levels: int = 5):
        """
        Initialize order book depth tracker.
        
        Args:
            levels: Number of levels to track on each side
        """
        self.levels = levels
        self._bids: List[Tuple[float, float]] = []  # (price, size)
        self._asks: List[Tuple[float, float]] = []
        self._bid_depth: float = 0.0
        self._ask_depth: float = 0.0
    
    def update_bids(self, bids: List[Tuple[float, float]]) -> None:
        """
        Update bid levels.
        
        Args:
            bids: List of (price, size) tuples, sorted by price descending
        """
        self._bids = bids[:self.levels]
        self._bid_depth = sum(size for _, size in self._bids)
    
    def update_asks(self, asks: List[Tuple[float, float]]) -> None:
        """
        Update ask levels.
        
        Args:
            asks: List of (price, size) tuples, sorted by price ascending
        """
        self._asks = asks[:self.levels]
        self._ask_depth = sum(size for _, size in self._asks)
    
    def get_bid_depth(self) -> float:
        """Get total bid depth for tracked levels."""
        return self._bid_depth
    
    def get_ask_depth(self) -> float:
        """Get total ask depth for tracked levels."""
        return self._ask_depth
    
    def get_best_bid(self) -> Optional[float]:
        """Get best bid price."""
        return self._bids[0][0] if self._bids else None
    
    def get_best_ask(self) -> Optional[float]:
        """Get best ask price."""
        return self._asks[0][0] if self._asks else None
    
    def get_mid_price(self) -> Optional[float]:
        """Get mid price."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if best_bid and best_ask:
            return (best_bid + best_ask) / 2
        return None
    
    def get_spread(self) -> Optional[float]:
        """Get bid-ask spread."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if best_bid and best_ask:
            return best_ask - best_bid
        return None
    
    def get_depth_imbalance(self) -> float:
        """
        Get depth imbalance ratio.
        Positive = more bid depth, Negative = more ask depth.
        """
        total_depth = self._bid_depth + self._ask_depth
        if total_depth == 0:
            return 0.0
        return (self._bid_depth - self._ask_depth) / total_depth
    
    def clear(self) -> None:
        """Clear all data."""
        self._bids.clear()
        self._asks.clear()
        self._bid_depth = 0.0
        self._ask_depth = 0.0
