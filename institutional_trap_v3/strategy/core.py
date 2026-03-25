import pandas as pd
import numpy as np
import asyncio
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from config import Config
from execution.mt5_client import MT5Client
from utils.logger import get_logger

logger = get_logger("Strategy")

class SMCEngine:
    def __init__(self):
        # State: 'IDLE', 'SWEEP_DETECTED', 'INVALIDATED'
        self.state = 'IDLE'
        self.mt5 = MT5Client()
        
        # 1H Range Data
        self.range_high = None
        self.range_low = None
        self.range_start_time = None # Time when current range was fetched
        self.last_fetch_time = None  # Timestamp of last fetch (for 60m lock)
        self.entry_count = 0 # Count of entries taken in current range, for ML feature tracking
        self.MAX_ENTRIES = 1 # Max entries per sweep to prevent overtrading
        self.ENTRY_COOLDOWN_SEC = 60 # Minimum seconds between entries in the same range, for ML feature tracking
        self.last_entry_time = None # Timestamp of last entry taken, for cooldown tracking
        # Sweep Data
        self.sweep_direction = None # 'LONG' (swept low) or 'SHORT' (swept high)
        self.order_block_high = None
        self.order_block_low = None
        self.sweep_time = None
        self.sweep_wick_extreme = None # Store the extreme wick price for SL calculation
        

    def get_current_state(self):
        return {
            'state': self.state,
            'range_high': self.range_high,
            'range_low': self.range_low,
            'sweep_dir': self.sweep_direction,
            'ob_high': self.order_block_high,
            'ob_low': self.order_block_low
        }

    def analyze_1h_range(self, df_1h):
        """
        Call this ONLY when state is IDLE and we need to fetch levels.
        Checks 60-min cooldown.
        Returns True if new levels fetched, False otherwise.
        """
        now = datetime.now()
        
        # Check Cooldown: Must be 60 mins since last fetch
        if self.last_fetch_time:
            elapsed = now - self.last_fetch_time
            if elapsed < timedelta(minutes=60):
                if not hasattr(self, '_wait_message_printed') or not self._wait_message_printed:
                    logger.info(f"Level Lock Active: Waiting {60 - elapsed.total_seconds()/60:.1f} more mins.")
                    self._wait_message_printed = True
                return False
        else:
            self._wait_message_printed = False

        if len(df_1h) < 2:
            return False

        # Get last CLOSED hourly candle (iloc[-2] because iloc[-1] is forming)
        last_closed = df_1h.iloc[-2] 
        
        self.range_high = last_closed['high']
        self.range_low = last_closed['low']
        self.range_start_time = last_closed['time']
        self.last_fetch_time = now
        
        self.state = 'IDLE'
        logger.info(f"New 1H Range Fetch: High={self.range_high}, Low={self.range_low}. Locked for 60m.")
        return True

    def analyze_5m_sweep(self, df_5m, range_high, range_low, range_start_time, df_1h):
        """
        Scans 5m candles for sweep. 
        IMMEDIATELY checks trend alignment. If against trend -> INVALIDATE.
        """
        if len(df_5m) < 2:
            return None

        # 1. Identify Time Boundary
        #mask = (df_5m['time'] > range_start_time) & (df_5m.index < len(df_5m) - 1)
        scan_df = df_5m

        if scan_df.empty:
            return None
            print("No 5m data to scan for sweeps.")

        candidate = scan_df.iloc[-2]
        swept_low = candidate['low'] < range_low and candidate['close'] > range_low
        swept_high = candidate['high'] > range_high and candidate['close'] < range_high

        # If no sweep happened, check for Range Breakout (Invalidation Rule 1)
        if not swept_low and not swept_high:
            close_out_up = candidate['close'] > range_high
            close_out_down = candidate['close'] < range_low
            if close_out_up or close_out_down:
                logger.info(f"Range Broken (No Sweep). Invalidating.")
                return {'type': 'INVALIDATE'}
            return None

        # 2. Determine Potential Direction
        potential_dir = None
        if swept_low:
            potential_dir = 'LONG' # Swept low, expect bounce up
            ob_high = max(candidate['high'], candidate['low'])
            ob_low = min(candidate['high'], candidate['low'])
            print(f"Sweep Low Detected at {candidate['time']}. OB: {ob_low}-{ob_high}")
        elif swept_high:
            potential_dir = 'SHORT' # Swept high, expect drop down
            ob_high = max(candidate['high'], candidate['low'])
            ob_low = min(candidate['high'], candidate['low'])
            print(f"Sweep High Detected at {candidate['time']}. OB: {ob_low}-{ob_high}")

        # 3. IMMEDIATE TREND CHECK
        # We need 1H data here to confirm trend before accepting the sweep
        if df_1h is not None and len(df_1h) > 200:
            trend = self.get_trend_direction(df_1h)
            print(f"Trend Check: {trend}, Potential Sweep Direction: {potential_dir}")
            
            if potential_dir == 'LONG' and trend != 'UP':
                logger.warning(f"Sweep LONG detected, but Trend is {trend}. INVALIDATING.")
                return {'type': 'INVALIDATE'}
            
            if potential_dir == 'SHORT' and trend != 'DOWN':
                logger.warning(f"Sweep SHORT detected, but Trend is {trend}. INVALIDATING.")
                return {'type': 'INVALIDATE'}
                
            if trend == 'NEUTRAL':
                logger.warning("Trend is Neutral (Price ~ EMA). Skipping Setup.")
                return None
        else:
            logger.warning("1H Data not available for Trend Check. Proceeding with caution.")
        
        # Store the extreme wick for SL calculation later
        sweep_wick_extreme = candidate['low'] if potential_dir == 'LONG' else candidate['high']

        logger.info(f"Sweep Detected ({potential_dir}) aligned with Trend. OB: {ob_low}-{ob_high}")
        
        return {
            'type': 'SWEEP',
            'direction': potential_dir,
            'ob_high': ob_high,
            'ob_low': ob_low,
            'sweep_wick_extreme': sweep_wick_extreme,
            'time': candidate['time']
        }

    def analyze_1m_entry(self, df_1m, ob_high, ob_low, direction, sweep_wick_extreme, range_high, range_low, df_1h=None):
        """
        Checks last 2 CLOSED 1m candles for confirmation patterns.
        Returns FULL SIGNAL dict if entry found.
        """
        now = datetime.now()

        # 1. Check Max Entries Limit
        if self.entry_count >= self.MAX_ENTRIES:
            return None  # Stop signaling after 3 trades

        # 2. Check Time Cooldown (1 minute)
        if self.last_entry_time:
            elapsed = (now - self.last_entry_time).total_seconds()
            if elapsed < self.ENTRY_COOLDOWN_SEC:
                return None  # Wait for cooldown

        if len(df_1m) < 3:
            return None
            
        c1 = df_1m.iloc[-3] # Older
        c2 = df_1m.iloc[-2] # Newest (Just closed)
        
        # Define OB Range
        ob_top = ob_high
        ob_bot = ob_low
        
        # Check Overlap: At least one candle must touch the OB
        # For Long: Low of candles <= OB Top
        # For Short: High of candles >= OB Bot
        overlap = False
        in_ob_c1_low = ob_bot <= c1['low'] <= ob_top
        in_ob_c1_high = ob_bot <= c1['high'] <= ob_top      
        in_ob_c2_low = ob_bot <= c2['low'] <= ob_top
        in_ob_c2_high = ob_bot <= c2['high'] <= ob_top
    
        if in_ob_c1_low or in_ob_c1_high or in_ob_c2_low or in_ob_c2_high:
                overlap = True
        else:
            overlap = False

        if not overlap:
            # Invalidation Rule 4 Check: Price moved away completely
            if direction == 'LONG':
                if c2['close'] < ob_bot and c2['high'] < ob_bot:
                    logger.info("Price rejected OB downwards. Invalidating.")
                    return {'type': 'INVALIDATE'}
            if direction == 'SHORT':
                if c2['close'] > ob_top and c2['low'] > ob_top:
                    logger.info("Price rejected OB upwards. Invalidating.")
                    return {'type': 'INVALIDATE'}
            return None

        pattern_name = None
        entry_price = c2['close']
        
        # Check Patterns
        if direction == 'LONG':
            if self.is_bullish_engulfing(c1, c2):
                pattern_name = "Bullish Engulfing"
            elif self.is_hammer(c2):
                pattern_name = "Hammer"
                    
        elif direction == 'SHORT':
            if self.is_bearish_engulfing(c1, c2):
                pattern_name = "Bearish Engulfing"
            elif self.is_shooting_star(c2):
                pattern_name = "Shooting Star"

        if pattern_name:
            logger.info(f"{pattern_name} Confirmation Found! (Trade #{self.entry_count + 1}) Preparing Signal.")

            # Calculate Stop Loss (Beyond Wick Extreme + Buffer)
            if direction == 'LONG':
                sl_price = sweep_wick_extreme - Config.SL_BUFFER_POINTS
                tp_price = 0.0 # Target opposite liquidity
            else:
                sl_price = sweep_wick_extreme + Config.SL_BUFFER_POINTS
                tp_price = 0.0
            
            # Validate SL/TP makes sense
            if direction == 'LONG' and sl_price >= entry_price:
                sl_price = entry_price - (ob_top - ob_bot) # Fallback to OB height
            if direction == 'SHORT' and sl_price <= entry_price:
                sl_price = entry_price + (ob_top - ob_bot)

            return {
                'type': 'ENTRY',
                'direction': direction,
                'entry_price': entry_price,
                'stop_loss': sl_price,
                'pattern': pattern_name,
                'features': { # For ML
                    'wick_ratio': 0.5, # Placeholder, calculate if needed
                    'body_ratio': 0.5,
                    'vol_ratio': 1.0,
                    'pattern_type': 1 if "Engulfing" in pattern_name else 2,
                    'hour': datetime.now().hour,
                    'direction': 1 if direction == 'LONG' else -1
                }
            }

        return None
    def get_trend_direction(self, df_1h):
        """
        Determines the current trend based on the 200 EMA on the 1H timeframe.
        
        Args:
            df_1h (pd.DataFrame): 1-Hour candlestick data with 'close' column.
            
        Returns:
            str: 'UP' if price > 200 EMA, 'DOWN' if price < 200 EMA, 'NEUTRAL' otherwise.
        """

        if df_1h is None or len(df_1h) < 200:
            return 'NEUTRAL'

        try:
            # Calculate 200 EMA
            ema_200 = df_1h['close'].ewm(span=200, adjust=False).mean()
            
            # Get the last CLOSED candle's close price and EMA value
            # We use iloc[-2] to ensure we are using confirmed data, not the forming candle
            last_close = df_1h.iloc[-2]['close']
            last_ema = ema_200.iloc[-2]

            # Determine Trend
            if last_close > last_ema:
                print(f"DEBUG: Last Close={last_close}, EMA200={last_ema}")
                return 'UP'
                
            elif last_close < last_ema:
                print(f"DEBUG: Last Close={last_close}, EMA200={last_ema}")
                return 'DOWN'
            else:
                return 'NEUTRAL'
                        
        except Exception as e:
            logger.error(f"Error calculating trend direction: {e}")
            return 'NEUTRAL'
        
    # --- Pattern Helpers ---
    def is_bullish_engulfing(self, c1, c2):
        if c2['close'] <= c2['open']: return False
        if c1['close'] >= c1['open']: return False
        #print(f"Bullish Engulfing: C1 Open={c1['open']}, C1 Close={c1['close']}, C2 Open={c2['open']}, C2 Close={c2['close']}")
        return c2['open'] < c1['close'] and c2['close'] > c1['open']
    
    def is_hammer(self, c):
        body = abs(c['close'] - c['open'])
        if body == 0: return False
        lower_wick = min(c['close'], c['open']) - c['low']
        upper_wick = c['high'] - max(c['close'], c['open'])
        #print(f"Hammer: Body={body}, Lower Wick={lower_wick}, Upper Wick={upper_wick}")
        return (lower_wick > body * 2) and (upper_wick < body * 0.5) and (c['close'] > c['open'])

    def is_bearish_engulfing(self, c1, c2):
        if c2['close'] >= c2['open']: return False
        if c1['close'] <= c1['open']: return False
        #print(f"Bearish Engulfing: C1 Open={c1['open']}, C1 Close={c1['close']}, C2 Open={c2['open']}, C2 Close={c2['close']}")
        return c2['open'] > c1['close'] and c2['close'] < c1['open']

    def is_shooting_star(self, c):
        body = abs(c['close'] - c['open'])
        if body == 0: return False
        lower_wick = min(c['close'], c['open']) - c['low']
        upper_wick = c['high'] - max(c['close'], c['open'])
        #print(f"Shooting Star: Body={body}, Lower Wick={lower_wick}, Upper Wick={upper_wick}")
        return (upper_wick > body * 2) and (lower_wick < body * 0.5) and (c['close'] < c['open'])

    def invalidate_setup(self):
        logger.warning("Setup Invalidated. Entering Cooldown.")
        self.state = 'INVALIDATED'
        self.entry_count = 0
        self.last_entry_time = None
        self.sweep_direction = None
        self.order_block_high = None
        self.order_block_low = None
        self.sweep_wick_extreme = None