"""
Position manager for Institutional Trap v3.0.
Handles intelligent trailing stop management with ATR-based logic.
"""

import asyncio
import time
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

from config import Config
from .exchange_client import ExchangeClient
from strategy.indicators import MomentumDetector


logger = logging.getLogger("institutional_trap_v3")


class PositionAction(Enum):
    """Position management action."""
    NONE = "none"
    UPDATE_STOP = "update_stop"
    EXIT = "exit"


@dataclass
class PositionState:
    """Current position state."""
    direction: int  # 1 for long, -1 for short
    entry_price: float
    current_stop: float
    highest_price: float = 0.0
    lowest_price: float = 0.0
    atr_multiplier: float = 2.0
    entry_time: int = 0
    breakeven_triggered: bool = False
    contracts: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'direction': 'LONG' if self.direction > 0 else 'SHORT',
            'entry_price': self.entry_price,
            'current_stop': self.current_stop,
            'highest_price': self.highest_price,
            'lowest_price': self.lowest_price,
            'atr_multiplier': self.atr_multiplier,
            'entry_time': self.entry_time,
            'breakeven_triggered': self.breakeven_triggered,
            'contracts': self.contracts,
        }


class PositionManager:
    """
    Manages active position with intelligent trailing stop.
    Implements symmetric logic for both long and short positions.
    """
    
    def __init__(self, config: Config, exchange_client: ExchangeClient):
        """
        Initialize position manager.
        
        Args:
            config: Configuration object
            exchange_client: Exchange client instance
        """
        self.config = config
        self.exchange = exchange_client
        
        # Current position state
        self.position: Optional[PositionState] = None
        
        # Momentum detector for trailing stop adjustment
        self.momentum_detector = MomentumDetector(config.MOMENTUM_EVALUATION_PERIOD)
        
        # Time limit
        self.time_limit_seconds = config.TIME_LIMIT_MINUTES * 60
    
    def open_position(
        self,
        direction: int,
        entry_price: float,
        contracts: float,
        atr: float
    ) -> None:
        """
        Open new position with initial stop loss.
        
        Args:
            direction: 1 for long, -1 for short
            entry_price: Entry price
            contracts: Position size in contracts
            atr: Current ATR value
        """
        # Calculate initial stop loss
        if direction > 0:  # Long
            initial_stop = entry_price - (self.config.INITIAL_STOP_ATR_MULTIPLIER * atr)
        else:  # Short
            initial_stop = entry_price + (self.config.INITIAL_STOP_ATR_MULTIPLIER * atr)
        
        self.position = PositionState(
            direction=direction,
            entry_price=entry_price,
            current_stop=initial_stop,
            highest_price=entry_price if direction > 0 else 0.0,
            lowest_price=entry_price if direction < 0 else 0.0,
            atr_multiplier=self.config.TRAILING_STOP_ATR_MULTIPLIER_BASE,
            entry_time=int(time.time()),
            breakeven_triggered=False,
            contracts=contracts,
        )
        
        logger.info(
            f"Position opened: {'LONG' if direction > 0 else 'SHORT'} @ {entry_price}, "
            f"stop: {initial_stop}, contracts: {contracts}"
        )
    
    def update(self, current_price: float, current_delta: float) -> Tuple[PositionAction, Optional[float]]:
        """
        Update position state based on current price.
        
        Args:
            current_price: Current mark price
            current_delta: Current bar delta for momentum detection
        
        Returns:
            Tuple of (action, new_stop_price)
        """
        if self.position is None:
            return PositionAction.NONE, None
        
        pos = self.position
        
        # Update extreme prices
        if pos.direction > 0:  # Long
            if current_price > pos.highest_price:
                pos.highest_price = current_price
        else:  # Short
            if current_price < pos.lowest_price or pos.lowest_price == 0:
                pos.lowest_price = current_price
        
        # Check time limit
        elapsed = time.time() - pos.entry_time
        if elapsed > self.time_limit_seconds:
            logger.info(f"Time limit reached ({elapsed/60:.1f} min), closing position")
            return PositionAction.EXIT, None
        
        # Check breakeven trigger
        if not pos.breakeven_triggered:
            if pos.direction > 0:  # Long
                profit_distance = current_price - pos.entry_price
                if profit_distance >= self.config.BREAKEVEN_ATR_MULTIPLIER * self._get_atr_for_position():
                    pos.breakeven_triggered = True
                    pos.current_stop = pos.entry_price
                    logger.info("Breakeven triggered for LONG position")
                    return PositionAction.UPDATE_STOP, pos.entry_price
            else:  # Short
                profit_distance = pos.entry_price - current_price
                if profit_distance >= self.config.BREAKEVEN_ATR_MULTIPLIER * self._get_atr_for_position():
                    pos.breakeven_triggered = True
                    pos.current_stop = pos.entry_price
                    logger.info("Breakeven triggered for SHORT position")
                    return PositionAction.UPDATE_STOP, pos.entry_price
        
        # If not yet breakeven, no trailing stop updates
        if not pos.breakeven_triggered:
            return PositionAction.NONE, None
        
        # Calculate trailing stop
        new_stop = self._calculate_trailing_stop(pos, current_price, current_delta)
        
        # Update stop if it moved favorably
        if pos.direction > 0:  # Long (stop only moves up)
            if new_stop > pos.current_stop:
                pos.current_stop = new_stop
                return PositionAction.UPDATE_STOP, new_stop
        else:  # Short (stop only moves down)
            if new_stop < pos.current_stop:
                pos.current_stop = new_stop
                return PositionAction.UPDATE_STOP, new_stop
        
        return PositionAction.NONE, None
    
    def _calculate_trailing_stop(
        self,
        pos: PositionState,
        current_price: float,
        current_delta: float
    ) -> float:
        """
        Calculate trailing stop with intelligent multiplier adjustment.
        
        Args:
            pos: Current position state
            current_price: Current price
            current_delta: Current bar delta
        
        Returns:
            Calculated stop price
        """
        atr = self._get_atr_for_position()
        
        # Detect momentum
        is_strong_momentum = self.momentum_detector.update(current_delta)
        
        # Adjust multiplier based on momentum
        if is_strong_momentum:
            pos.atr_multiplier = self.config.TRAILING_STOP_ATR_MULTIPLIER_BASE
        else:
            pos.atr_multiplier = self.config.TRAILING_STOP_ATR_MULTIPLIER_WEAK
        
        # Calculate base trailing stop
        if pos.direction > 0:  # Long
            base_stop = pos.highest_price - (pos.atr_multiplier * atr)
            # Ensure stop doesn't go below entry after breakeven
            return max(base_stop, pos.entry_price)
        else:  # Short
            base_stop = pos.lowest_price + (pos.atr_multiplier * atr)
            # Ensure stop doesn't go above entry after breakeven
            return min(base_stop, pos.entry_price)
    
    def _get_atr_for_position(self) -> float:
        """Get current ATR (would need to be passed in or fetched)."""
        # This is a placeholder - in practice, ATR should be passed to update()
        # For now, we'll use a default that should be overridden
        return 100.0  # Placeholder
    
    def check_stop_loss(self, current_price: float) -> bool:
        """
        Check if stop loss has been hit.
        
        Args:
            current_price: Current mark price
        
        Returns:
            True if stop loss hit
        """
        if self.position is None:
            return False
        
        pos = self.position
        
        if pos.direction > 0:  # Long
            return current_price <= pos.current_stop
        else:  # Short
            return current_price >= pos.current_stop
    
    async def close_position(self) -> Optional[Dict[str, Any]]:
        """
        Close current position via exchange.
        
        Returns:
            Order response or None if no position
        """
        if self.position is None:
            return None
        
        try:
            # Fetch current position from exchange
            exchange_pos = await self.exchange.fetch_position(
                self.config.get_symbol_for_ccxt()
            )
            
            if exchange_pos:
                result = await self.exchange.close_position(
                    self.config.get_symbol_for_ccxt(),
                    exchange_pos
                )
                
                pnl = float(exchange_pos.get('unrealizedPnl', 0))
                side = exchange_pos['side']
                
                logger.info(
                    f"Position closed: {side}, PnL: {pnl:.2f} USDT"
                )
                
                # Clear position state
                self.position = None
                
                return result
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
        
        return None
    
    def get_unrealized_pnl(self, current_price: float) -> float:
        """
        Calculate unrealized PnL.
        
        Args:
            current_price: Current mark price
        
        Returns:
            Unrealized PnL in quote currency
        """
        if self.position is None:
            return 0.0
        
        pos = self.position
        
        if pos.direction > 0:  # Long
            return (current_price - pos.entry_price) * pos.contracts
        else:  # Short
            return (pos.entry_price - current_price) * pos.contracts
    
    def get_position_info(self) -> Optional[Dict[str, Any]]:
        """Get current position information."""
        if self.position is None:
            return None
        return self.position.to_dict()
    
    def has_position(self) -> bool:
        """Check if position is open."""
        return self.position is not None
    
    def reset(self) -> None:
        """Reset position manager state."""
        self.position = None
        self.momentum_detector.clear()
