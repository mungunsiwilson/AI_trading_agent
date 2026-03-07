"""
Core strategy logic for Institutional Trap v3.0.
Implements the symmetric "Reaction Time" model for both long and short entries.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np

from config import Config
from strategy.indicators import VWMA, ATR, DeltaCalculator, MomentumDetector
from data.buffers import CircularBuffer, OrderBookDepth


logger = logging.getLogger("institutional_trap_v3")


class Direction(Enum):
    """Trade direction."""
    LONG = 1
    SHORT = -1


@dataclass
class EntrySignal:
    """Entry signal data structure."""
    direction: Direction
    entry_price: float
    signal_type: str
    confidence: float  # 0-1 confidence score
    timestamp: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'direction': self.direction.name,
            'entry_price': self.entry_price,
            'signal_type': self.signal_type,
            'confidence': self.confidence,
            'timestamp': self.timestamp,
        }


class StrategyCore:
    """
    Core strategy implementation for Institutional Trap v3.0.
    Symmetric logic for both long and short positions.
    """
    
    def __init__(self, config: Config):
        """
        Initialize strategy core.
        
        Args:
            config: Configuration object
        """
        self.config = config
        
        # Indicators
        self.vwma_h1 = VWMA(config.VWMA_PERIOD_H1)
        self.atr_m1 = ATR(config.ATR_PERIOD)
        self.delta_calc = DeltaCalculator(config.DELTA_AVERAGE_PERIOD)
        self.momentum_detector = MomentumDetector(config.MOMENTUM_EVALUATION_PERIOD)
        
        # Data buffers for 1-minute bars
        self.highs_m1 = CircularBuffer(maxlen=50)
        self.lows_m1 = CircularBuffer(maxlen=50)
        self.closes_m1 = CircularBuffer(maxlen=50)
        self.volumes_m1 = CircularBuffer(maxlen=50)
        self.deltas_m1 = CircularBuffer(maxlen=50)
        
        # State tracking
        self._current_bar_open: Optional[float] = None
        self._current_bar_high: Optional[float] = None
        self._current_bar_low: Optional[float] = None
        self._current_bar_close: Optional[float] = None
        self._current_bar_volume: Optional[float] = None
        self._current_bar_timestamp: Optional[int] = None
        
        # Order book state
        self._orderbook_depth = OrderBookDepth(config.ORDERBOOK_LEVELS)
        self._bid_depth_before_sweep: float = 0.0
        self._ask_depth_before_sweep: float = 0.0
        
        # Tick speed tracking
        self._trades_per_second: float = 0.0
        self._trades_per_second_during_sweep: float = 0.0
        self._last_trade_time: int = 0
        self._recent_trade_count: int = 0
        
        # Sweep detection state
        self._sweep_detected: bool = False
        self._sweep_direction: Optional[Direction] = None
        self._sweep_price: float = 0.0
        self._bars_since_sweep: int = 0
        self._absorption_confirmed: bool = False
        
        # Current market state
        self._current_mark_price: float = 0.0
        self._h1_vwma: float = 0.0
    
    def update_h1_candle(self, close: float, volume: float) -> float:
        """
        Update 1-hour VWMA with new candle.
        
        Args:
            close: Candle close price
            volume: Candle volume
        
        Returns:
            Updated VWMA value
        """
        self._h1_vwma = self.vwma_h1.update(close, volume)
        return self._h1_vwma
    
    def update_m1_candle(
        self,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        delta: float,
        timestamp: int
    ) -> None:
        """
        Update 1-minute bar data.
        
        Args:
            open_price: Candle open
            high: Candle high
            low: Candle low
            close: Candle close
            volume: Candle volume
            delta: Bar delta (buy vol - sell vol)
            timestamp: Bar timestamp
        """
        self.highs_m1.append(high)
        self.lows_m1.append(low)
        self.closes_m1.append(close)
        self.volumes_m1.append(volume)
        self.deltas_m1.append(delta)
        
        # Update ATR
        self.atr_m1.update(high, low, close)
        
        # Store current bar info
        self._current_bar_open = open_price
        self._current_bar_high = high
        self._current_bar_low = low
        self._current_bar_close = close
        self._current_bar_volume = volume
        self._current_bar_timestamp = timestamp
    
    def update_mark_price(self, price: float) -> None:
        """Update current mark price."""
        self._current_mark_price = price
    
    def update_orderbook(self, bids: List[Tuple[float, float]], asks: List[Tuple[float, float]]) -> None:
        """
        Update order book depth.
        
        Args:
            bids: List of (price, size) tuples
            asks: List of (price, size) tuples
        """
        self._orderbook_depth.update_bids(bids)
        self._orderbook_depth.update_asks(asks)
    
    def add_trade(self, price: float, size: float, side: str, timestamp: int) -> None:
        """
        Add trade for tick speed calculation.
        
        Args:
            price: Trade price
            size: Trade size
            side: Trade side ('buy' or 'sell')
            timestamp: Trade timestamp in ms
        """
        # Calculate trades per second
        if self._last_trade_time > 0:
            time_diff_ms = timestamp - self._last_trade_time
            if time_diff_ms > 0:
                self._recent_trade_count += 1
                # Rolling average over 1 second
                if time_diff_ms >= 1000:
                    self._trades_per_second = self._recent_trade_count / (time_diff_ms / 1000)
                    self._recent_trade_count = 0
        else:
            self._recent_trade_count = 1
        
        self._last_trade_time = timestamp
        
        # Add to delta calculator
        self.delta_calc.add_trade(price, size, side, timestamp)
    
    def finalize_bar(self) -> float:
        """
        Finalize current bar delta.
        
        Returns:
            Bar delta
        """
        return self.delta_calc.finalize_bar()
    
    def _check_macro_trend(self, direction: Direction) -> bool:
        """
        Check Layer 1: Macro trend filter.
        
        Args:
            direction: Intended trade direction
        
        Returns:
            True if macro trend allows entry
        """
        if not self.vwma_h1.is_ready():
            return False
        
        if direction == Direction.LONG:
            return self._current_mark_price > self._h1_vwma
        else:  # SHORT
            return self._current_mark_price < self._h1_vwma
    
    def _check_exhaustion_signal(self, direction: Direction) -> Tuple[bool, bool]:
        """
        Check Layer 2: Exhaustion signal (sweep + absorption).
        
        Args:
            direction: Intended trade direction
        
        Returns:
            Tuple of (sweep_detected, absorption_confirmed)
        """
        if len(self.deltas_m1) < self.config.DELTA_AVERAGE_PERIOD:
            return False, False
        
        deltas = self.deltas_m1.get_array()
        lows = self.lows_m1.get_array()
        highs = self.highs_m1.get_array()
        
        avg_abs_delta = self.delta_calc.get_average_abs_delta()
        if avg_abs_delta == 0:
            return False, False
        
        spike_threshold = self.config.DELTA_SPIKE_MULTIPLIER * avg_abs_delta
        
        # Check for sweep in opposite direction
        if direction == Direction.LONG:
            # Look for new 10-period low with massive sell volume
            if len(lows) >= self.config.DELTA_SWEEP_PERIOD_M1:
                recent_lows = lows[-self.config.DELTA_SWEEP_PERIOD_M1:]
                current_low = lows[-1]
                
                # Check if we made a new low
                is_new_low = current_low <= np.min(recent_lows[:-1]) if len(recent_lows) > 1 else True
                
                # Check if delta is significantly negative
                current_delta = deltas[-1]
                is_negative_spike = current_delta < -spike_threshold
                
                if is_new_low and is_negative_spike:
                    self._sweep_detected = True
                    self._sweep_direction = Direction.LONG
                    self._sweep_price = current_low
                    self._bars_since_sweep = 0
                    self._bid_depth_before_sweep = self._orderbook_depth.get_bid_depth()
                    return True, False
        
        else:  # SHORT
            # Look for new 10-period high with massive buy volume
            if len(highs) >= self.config.DELTA_SWEEP_PERIOD_M1:
                recent_highs = highs[-self.config.DELTA_SWEEP_PERIOD_M1:]
                current_high = highs[-1]
                
                # Check if we made a new high
                is_new_high = current_high >= np.max(recent_highs[:-1]) if len(recent_highs) > 1 else True
                
                # Check if delta is significantly positive
                current_delta = deltas[-1]
                is_positive_spike = current_delta > spike_threshold
                
                if is_new_high and is_positive_spike:
                    self._sweep_detected = True
                    self._sweep_direction = Direction.SHORT
                    self._sweep_price = current_high
                    self._bars_since_sweep = 0
                    self._ask_depth_before_sweep = self._orderbook_depth.get_ask_depth()
                    return True, False
        
        # If sweep was previously detected, check for absorption
        if self._sweep_detected and self._sweep_direction == direction:
            self._bars_since_sweep += 1
            
            # Check if we're within the absorption window (1-3 bars)
            if self._bars_since_sweep > self.config.ABSORPTION_BARS_MAX:
                self._sweep_detected = False
                return False, False
            
            # Check that price hasn't made a new extreme
            if direction == Direction.LONG:
                if len(lows) >= 2 and lows[-1] < self._sweep_price:
                    # New low made, invalidates setup
                    self._sweep_detected = False
                    return False, False
                
                # Check cumulative delta is flat or positive
                cum_delta = self.delta_calc.get_cumulative_delta(self._bars_since_sweep)
                absorption = cum_delta >= 0
                
            else:  # SHORT
                if len(highs) >= 2 and highs[-1] > self._sweep_price:
                    # New high made, invalidates setup
                    self._sweep_detected = False
                    return False, False
                
                # Check cumulative delta is flat or negative
                cum_delta = self.delta_calc.get_cumulative_delta(self._bars_since_sweep)
                absorption = cum_delta <= 0
            
            if absorption and self._bars_since_sweep >= self.config.ABSORPTION_BARS_MIN:
                self._absorption_confirmed = True
                return True, True
        
        return self._sweep_detected, self._absorption_confirmed
    
    def _check_micro_structure(self, direction: Direction) -> bool:
        """
        Check Layer 3: Micro-structure trigger.
        
        Args:
            direction: Intended trade direction
        
        Returns:
            True if micro-structure conditions are met
        """
        # Check tick speed drop
        if self._trades_per_second_during_sweep == 0:
            return False
        
        tick_speed_ratio = self._trades_per_second / self._trades_per_second_during_sweep
        tick_speed_drop = tick_speed_ratio < self.config.TICK_SPEED_DROP_THRESHOLD
        
        # Check order book depth increase
        if direction == Direction.LONG:
            current_bid_depth = self._orderbook_depth.get_bid_depth()
            if self._bid_depth_before_sweep == 0:
                return False
            depth_increase = (current_bid_depth - self._bid_depth_before_sweep) / self._bid_depth_before_sweep
            depth_condition = depth_increase >= self.config.ORDERBOOK_DEPTH_INCREASE_THRESHOLD
        else:  # SHORT
            current_ask_depth = self._orderbook_depth.get_ask_depth()
            if self._ask_depth_before_sweep == 0:
                return False
            depth_increase = (current_ask_depth - self._ask_depth_before_sweep) / self._ask_depth_before_sweep
            depth_condition = depth_increase >= self.config.ORDERBOOK_DEPTH_INCREASE_THRESHOLD
        
        return tick_speed_drop and depth_condition
    
    def should_enter(self) -> Optional[EntrySignal]:
        """
        Main entry point: check all layers and return entry signal if conditions met.
        
        Returns:
            EntrySignal if entry conditions are met, None otherwise
        """
        # Check both directions based on trading mode
        directions_to_check = []
        
        if self.config.TRADING_MODE in ["BOTH", "LONG_ONLY"]:
            directions_to_check.append(Direction.LONG)
        if self.config.TRADING_MODE in ["BOTH", "SHORT_ONLY"]:
            directions_to_check.append(Direction.SHORT)
        
        for direction in directions_to_check:
            # Layer 1: Macro trend
            if not self._check_macro_trend(direction):
                continue
            
            # Layer 2: Exhaustion signal
            sweep_detected, absorption_confirmed = self._check_exhaustion_signal(direction)
            
            if not absorption_confirmed:
                continue
            
            # Layer 3: Micro-structure trigger
            if self._check_micro_structure(direction):
                # All conditions met!
                signal = EntrySignal(
                    direction=direction,
                    entry_price=self._current_mark_price,
                    signal_type="institutional_trap_v3",
                    confidence=0.8,  # Could be calculated based on signal strength
                    timestamp=self._current_bar_timestamp or 0,
                )
                
                # Reset state after signal
                self._sweep_detected = False
                self._absorption_confirmed = False
                self._bars_since_sweep = 0
                
                return signal
        
        return None
    
    def get_atr(self) -> float:
        """Get current ATR value."""
        return self.atr_m1.get_value()
    
    def is_ready(self) -> bool:
        """Check if strategy has enough data to generate signals."""
        return (
            self.vwma_h1.is_ready() and
            self.atr_m1.is_ready() and
            self.delta_calc.is_ready() and
            len(self.deltas_m1) >= self.config.DELTA_AVERAGE_PERIOD
        )
    
    def reset(self) -> None:
        """Reset all state."""
        self.vwma_h1.clear()
        self.atr_m1.clear()
        self.delta_calc.clear()
        self.momentum_detector.clear()
        self.highs_m1.clear()
        self.lows_m1.clear()
        self.closes_m1.clear()
        self.volumes_m1.clear()
        self.deltas_m1.clear()
        
        self._sweep_detected = False
        self._absorption_confirmed = False
        self._bars_since_sweep = 0
