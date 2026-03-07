"""
Efficient indicator calculations for Institutional Trap v3.0.
Uses incremental formulas and numpy for performance.
"""

import numpy as np
from typing import Optional, List
from collections import deque


class VWMA:
    """
    Volume-Weighted Moving Average calculator.
    Uses incremental formula for efficiency.
    """
    
    def __init__(self, period: int):
        """
        Initialize VWMA calculator.
        
        Args:
            period: Number of periods for VWMA
        """
        self.period = period
        self._price_volume_sum: deque = deque(maxlen=period)
        self._volume_sum: deque = deque(maxlen=period)
        self._running_pv_sum: float = 0.0
        self._running_v_sum: float = 0.0
    
    def update(self, price: float, volume: float) -> float:
        """
        Update with new price and volume, return current VWMA.
        
        Args:
            price: Current price (typically close or typical price)
            volume: Current volume
        
        Returns:
            Current VWMA value
        """
        pv = price * volume
        
        # If buffer is full, remove oldest values
        if len(self._price_volume_sum) == self.period:
            old_pv = self._price_volume_sum[0]
            old_v = self._volume_sum[0]
            self._running_pv_sum -= old_pv
            self._running_v_sum -= old_v
        
        # Add new values
        self._price_volume_sum.append(pv)
        self._volume_sum.append(volume)
        self._running_pv_sum += pv
        self._running_v_sum += volume
        
        return self.get_value()
    
    def get_value(self) -> float:
        """Get current VWMA value."""
        if self._running_v_sum == 0:
            return 0.0
        return self._running_pv_sum / self._running_v_sum
    
    def is_ready(self) -> bool:
        """Check if enough data has been collected."""
        return len(self._price_volume_sum) >= self.period
    
    def clear(self) -> None:
        """Clear all data."""
        self._price_volume_sum.clear()
        self._volume_sum.clear()
        self._running_pv_sum = 0.0
        self._running_v_sum = 0.0


class ATR:
    """
    Average True Range calculator using Wilder's smoothing method.
    Optimized for incremental updates.
    """
    
    def __init__(self, period: int = 10):
        """
        Initialize ATR calculator.
        
        Args:
            period: Number of periods for ATR (default 10)
        """
        self.period = period
        self._prev_close: Optional[float] = None
        self._tr_values: deque = deque(maxlen=period)
        self._atr_value: Optional[float] = None
        self._count: int = 0
    
    def update(self, high: float, low: float, close: float) -> float:
        """
        Update with new OHLC data, return current ATR.
        
        Args:
            high: Current high
            low: Current low
            close: Current close (previous close for first call)
        
        Returns:
            Current ATR value
        """
        # Calculate True Range
        if self._prev_close is None:
            tr = high - low
        else:
            tr = max(
                high - low,
                abs(high - self._prev_close),
                abs(low - self._prev_close)
            )
        
        self._prev_close = close
        self._count += 1
        
        if self._atr_value is None:
            # First value: simple average
            self._tr_values.append(tr)
            if len(self._tr_values) == self.period:
                self._atr_value = sum(self._tr_values) / self.period
        else:
            # Wilder's smoothing: ATR = (Prev ATR * (n-1) + Current TR) / n
            self._atr_value = (self._atr_value * (self.period - 1) + tr) / self.period
        
        return self._atr_value if self._atr_value else 0.0
    
    def get_value(self) -> float:
        """Get current ATR value."""
        return self._atr_value if self._atr_value else 0.0
    
    def is_ready(self) -> bool:
        """Check if ATR is calculated and ready."""
        return self._atr_value is not None
    
    def clear(self) -> None:
        """Clear all data."""
        self._prev_close = None
        self._tr_values.clear()
        self._atr_value = None
        self._count = 0


class DeltaCalculator:
    """
    Calculate and track Delta (buying volume - selling volume).
    Maintains rolling statistics for detection of extreme values.
    """
    
    def __init__(self, average_period: int = 20):
        """
        Initialize Delta calculator.
        
        Args:
            average_period: Period for rolling average of absolute Delta
        """
        self.average_period = average_period
        self._delta_buffer: deque = deque(maxlen=average_period)
        self._abs_delta_sum: float = 0.0
        self._current_bar_delta: float = 0.0
        self._current_bar_buy_volume: float = 0.0
        self._current_bar_sell_volume: float = 0.0
    
    def add_trade(self, price: float, size: float, side: str, timestamp: int) -> None:
        """
        Add a trade to current bar delta calculation.
        
        Args:
            price: Trade price
            size: Trade size
            side: 'buy' or 'sell' (taker side)
            timestamp: Trade timestamp in ms
        """
        if side.lower() == 'buy':
            self._current_bar_buy_volume += size
        else:
            self._current_bar_sell_volume += size
        
        self._current_bar_delta = self._current_bar_buy_volume - self._current_bar_sell_volume
    
    def finalize_bar(self) -> float:
        """
        Finalize current bar and return delta.
        Call this when bar closes.
        
        Returns:
            Delta for the completed bar
        """
        delta = self._current_bar_delta
        
        # Update rolling average
        if len(self._delta_buffer) == self.average_period:
            old_abs_delta = abs(self._delta_buffer[0])
            self._abs_delta_sum -= old_abs_delta
        
        self._delta_buffer.append(delta)
        self._abs_delta_sum += abs(delta)
        
        # Reset for next bar
        self._current_bar_delta = 0.0
        self._current_bar_buy_volume = 0.0
        self._current_bar_sell_volume = 0.0
        
        return delta
    
    def get_average_abs_delta(self) -> float:
        """Get rolling average of absolute Delta."""
        if len(self._delta_buffer) == 0:
            return 0.0
        return self._abs_delta_sum / len(self._delta_buffer)
    
    def get_recent_deltas(self, n: int) -> List[float]:
        """Get last n delta values."""
        if n >= len(self._delta_buffer):
            return list(self._delta_buffer)
        return list(self._delta_buffer)[-n:]
    
    def get_cumulative_delta(self, n: int) -> float:
        """Get cumulative delta for last n bars."""
        if n >= len(self._delta_buffer):
            return sum(self._delta_buffer)
        return sum(list(self._delta_buffer)[-n:])
    
    def is_spike(self, delta: float, multiplier: float = 2.5) -> bool:
        """
        Check if delta is a spike (extreme value).
        
        Args:
            delta: Current delta value
            multiplier: Multiplier for average to detect spike
        
        Returns:
            True if delta is a spike
        """
        avg_abs_delta = self.get_average_abs_delta()
        if avg_abs_delta == 0:
            return False
        return abs(delta) > multiplier * avg_abs_delta
    
    def is_ready(self) -> bool:
        """Check if enough data has been collected."""
        return len(self._delta_buffer) >= self.average_period
    
    def clear(self) -> None:
        """Clear all data."""
        self._delta_buffer.clear()
        self._abs_delta_sum = 0.0
        self._current_bar_delta = 0.0
        self._current_bar_buy_volume = 0.0
        self._current_bar_sell_volume = 0.0


class MomentumDetector:
    """
    Detect momentum changes based on Delta strength.
    Used for intelligent trailing stop adjustment.
    """
    
    def __init__(self, evaluation_period: int = 5):
        """
        Initialize momentum detector.
        
        Args:
            evaluation_period: Number of previous bars to compare against
        """
        self.evaluation_period = evaluation_period
        self._delta_history: deque = deque(maxlen=evaluation_period + 1)
    
    def update(self, delta: float) -> bool:
        """
        Update with new delta and return if momentum is strong.
        
        Args:
            delta: Current bar delta
        
        Returns:
            True if momentum is strong (above average)
        """
        self._delta_history.append(delta)
        
        if len(self._delta_history) <= 1:
            return False
        
        # Compare against average of previous bars
        history = list(self._delta_history)[:-1]  # Exclude current
        if len(history) == 0:
            return False
        
        avg_delta = sum(history) / len(history)
        
        # Strong momentum if current delta > average
        return delta > avg_delta
    
    def get_average(self) -> float:
        """Get average delta of recent bars."""
        if len(self._delta_history) == 0:
            return 0.0
        return sum(self._delta_history) / len(self._delta_history)
    
    def clear(self) -> None:
        """Clear all data."""
        self._delta_history.clear()
