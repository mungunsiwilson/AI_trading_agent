"""
Helper utilities for Institutional Trap v3.0
"""

from datetime import datetime, timezone
from typing import Optional


def format_price(price: float, precision: int = 2) -> str:
    """Format price with specified precision."""
    return f"{price:.{precision}f}"


def format_size(size: float, precision: int = 4) -> str:
    """Format position size with specified precision."""
    return f"{size:.{precision}f}"


def timestamp_to_datetime(timestamp_ms: int) -> datetime:
    """Convert millisecond timestamp to datetime object."""
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)


def get_current_timestamp_ms() -> int:
    """Get current timestamp in milliseconds."""
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def calculate_position_size(
    position_size_usd: float,
    price: float,
    contract_size: float = 1.0
) -> float:
    """
    Calculate position size in contracts.
    
    Args:
        position_size_usd: Desired position size in USD
        price: Current price
        contract_size: Size of one contract (default 1.0 for most perps)
    
    Returns:
        Position size in contracts
    """
    if price <= 0:
        return 0.0
    return (position_size_usd / price) / contract_size


def normalize_price(price: float, tick_size: float) -> float:
    """Normalize price to exchange tick size."""
    if tick_size <= 0:
        return price
    return round(price / tick_size) * tick_size


def normalize_size(size: float, step_size: float) -> float:
    """Normalize size to exchange step size."""
    if step_size <= 0:
        return size
    return round(size / step_size) * step_size


def side_to_int(side: str) -> int:
    """Convert side string to integer (1 for buy/long, -1 for sell/short)."""
    return 1 if side.lower() in ['buy', 'long'] else -1


def side_to_str(side: int) -> str:
    """Convert side integer to string."""
    return 'LONG' if side > 0 else 'SHORT'


def opposite_side(side: str) -> str:
    """Get opposite side."""
    return 'SELL' if side.lower() == 'buy' else 'BUY'


def calculate_pnl(
    entry_price: float,
    exit_price: float,
    position_size: float,
    direction: int
) -> float:
    """
    Calculate PnL for a position.
    
    Args:
        entry_price: Entry price
        exit_price: Exit price
        position_size: Position size in contracts
        direction: 1 for long, -1 for short
    
    Returns:
        PnL in quote currency
    """
    if direction > 0:  # Long
        return (exit_price - entry_price) * position_size
    else:  # Short
        return (entry_price - exit_price) * position_size


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values."""
    if old_value == 0:
        return 0.0
    return ((new_value - old_value) / abs(old_value)) * 100
