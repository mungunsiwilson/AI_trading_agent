import asyncio
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta

from config import Config
from utils.logger import get_logger
from execution.mt5_client import MT5Client
from execution.position_manager import PositionManager
from strategy.core import SMCEngine
from ml.database import TradeDatabase
from ml.learner import MLTrainer
from notification.telegram_bot import TelegramBot

logger = get_logger("Main")

class TradingAgent:
    def __init__(self):
        self.mt5 = MT5Client()
        self.strategy = SMCEngine()
        self.pos_manager = PositionManager()
        self.db = TradeDatabase()
        self.ml = MLTrainer(self.db, Config.ML_MODEL_PATH)
        self.tg = TelegramBot(self)
        
        self.running = False
        self.last_5m_check = None
        
        # --- DATA CACHE SYSTEM ---
        self._cache = {'1h': None, '5m': None, '1m': None}
        self._cache_time = {'1h': None, '5m': None, '1m': None}
        self._cache_ttl = {
            '1h': timedelta(minutes=5),
            '5m': timedelta(minutes=1),
            '1m': timedelta(seconds=30)
        }
        
        # --- ANTI-SPAM TRACKING ---
        self._last_cooldown_log = None  # Track last cooldown log time
        self._cooldown_log_interval = timedelta(minutes=1)  # Log every 1 minute max

    def _get_cached_data(self, timeframe, mt5_tf, count, min_bars=10):
        """Cached data fetcher with TTL."""
        now = datetime.now()
        
        # Return cached data if fresh
        if (self._cache[timeframe] is not None and 
            self._cache_time[timeframe] is not None):
            age = now - self._cache_time[timeframe]
            if age < self._cache_ttl[timeframe]:
                return self._cache[timeframe]
        
        # Fetch fresh data
        rates = self.mt5.get_rates(Config.SYMBOL, mt5_tf, count)
        if rates is not None and len(rates) >= min_bars:
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            self._cache[timeframe] = df
            self._cache_time[timeframe] = now
            logger.debug(f"Fetched {len(df)} {timeframe} candles (cache refreshed)")
            return df
        elif self._cache[timeframe] is not None:
            logger.warning(f"Failed to fetch {timeframe}, using stale cache")
            return self._cache[timeframe]
        else:
            logger.error(f"Failed to fetch {timeframe} and no cache available")
            return None

    def _should_log_cooldown(self):
        """Anti-spam: Check if we should log cooldown message"""
        now = datetime.now()
        if self._last_cooldown_log is None:
            self._last_cooldown_log = now
            return True
        if now - self._last_cooldown_log >= self._cooldown_log_interval:
            self._last_cooldown_log = now
            return True
        return False

    def _invalidate_cache(self, timeframe=None):
        """Invalidate cache for specific timeframe or all"""
        if timeframe:
            self._cache[timeframe] = None
            self._cache_time[timeframe] = None
        else:
            for tf in self._cache:
                self._cache[tf] = None
                self._cache_time[tf] = None

    async def start(self):
        logger.info("Initializing SMC Agent (Strict 60m Lock)...")
        
        if not self.mt5.connect():
            logger.error("MT5 Connection Failed")
            await self.tg.send_message("🛑 **CRITICAL ERROR**: Failed to connect to MT5.")
            return
            
        self.db.init_db()
        if Config.ML_ENABLED:
            self.ml.load_model()
            count = self.db.get_trade_count()
            logger.info(f"ML Status: {count}/{Config.ML_MIN_TRADES} trades collected")
            
        await self.tg.start()
        
        await self.tg.send_message(
            f"✅ **Bot Started Successfully**\n"
            f"Symbol: `{Config.SYMBOL}`\n"
            f"Strategy: SMC Liquidity Sweep\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}\n"
            f"Status: _Scanning for setups..._"
        )
        
        self.running = True
        logger.info(f"Monitoring {Config.SYMBOL}...")
        
        try:
            while self.running:
                await self.loop()
                await asyncio.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            await self.tg.send_message("🛑 Bot stopped by user.")
        finally:
            self.shutdown()

    async def execute_trade(self, signal):
        """Executes the trade with robust error handling"""
        direction = signal['direction']
        entry_price = signal['entry_price']
        sl_price = signal['stop_loss']
        
        logger.info(f"Attempting to execute {direction} trade...")

        if Config.ML_ENABLED and self.ml.model:
            features = signal.get('features', {})
            if features:
                prob = self.ml.predict(signal, getattr(self, 'df_1m', None)) 
                if prob < Config.ML_THRESHOLD:
                    logger.info(f"❌ Trade FILTERED by ML (Prob: {prob:.2f})")
                    return False

        order_type = mt5.ORDER_TYPE_BUY if direction == 'LONG' else mt5.ORDER_TYPE_SELL
        
        request = self.mt5.build_order(
            symbol=Config.SYMBOL,
            type=order_type,
            volume=Config.LOT_SIZE,
            sl=sl_price,
            tp=0.0
        )
        
        if not request:
            logger.error("Failed to build order request.")
            await self.tg.send_message("❌ Order Build Failed")
            return False

        result = self.mt5.execute_order(request)

        if result is None:
            err = mt5.last_error()
            logger.error(f"Order execution returned None. Last Error: {err}")
            await self.tg.send_message(f"⚠️ **Execution Error**: {err}")
            return False
        
        retcode = result.retcode
        deal_id = result.deal

        logger.info(f"MT5 Order Send Raw Result: {result}")
        
        if retcode == mt5.TRADE_RETCODE_DONE or retcode == 10009:
            logger.info(f"✅ TRADE EXECUTED: {direction} @ {entry_price} | Deal ID: {deal_id}")
            
            risk_points = abs(entry_price - sl_price)
            
            self.pos_manager.init_position(
                direction=direction,
                entry_price=entry_price,
                sl=sl_price,
                risk_step=risk_points,
                entry_time=datetime.now()
            )
            self.strategy.state = 'IDLE'
            self._invalidate_cache('1m')
            
            await self.tg.send_entry_alert(direction, entry_price, sl_price, 0.0, signal.get('pattern', 'SMC'))
            return True
            
        else:
            comment = result.get('comment', 'Unknown')
            logger.error(f"❌ Order Failed: Retcode={retcode}, Comment={comment}")
            await self.tg.send_message(f"❌ **Order Failed**\nCode: `{retcode}`\nMsg: {comment}")
            return False

    async def loop(self):
        """Main Loop with Strict State & Time Logic"""
        try:
            now = datetime.now()
            
            df_1m = None
            df_5m = None
            df_1h = None

            # --- STATE: IDLE ---
            if self.strategy.state == 'IDLE':
                df_1h = self._get_cached_data('1h', mt5.TIMEFRAME_H1, 250, min_bars=200)
                df_5m = self._get_cached_data('5m', mt5.TIMEFRAME_M5, 20, min_bars=5)
                
            # --- STATE: INVALIDATED (Cooldown) ---
            elif self.strategy.state == 'INVALIDATED':
                if self.strategy.last_fetch_time:
                    elapsed = now - self.strategy.last_fetch_time
                    elapsed_minutes = elapsed.total_seconds() / 60.0
                    
                    if elapsed_minutes >= 60:
                        # Cooldown expired - fetch new data
                        logger.info("Cooldown expired. Fetching new 1H levels...")
                        df_1h = self._get_cached_data('1h', mt5.TIMEFRAME_H1, 250, min_bars=200)
                        # Don't return here - let it fall through to process the new range
                    else:
                        # Still in cooldown - manage position and return
                        remaining = 60 - elapsed_minutes
                        
                        # ANTI-SPAM: Only log every minute instead of every tick
                        if self._should_log_cooldown():
                            logger.info(f"Setup Invalidated. Cooldown: {remaining:.1f}m remaining.")
                        
                        await self.manage_position()
                        return  # Early return - don't process further
                else:
                    # No last_fetch_time - fetch as fallback
                    logger.warning("Invalidated state but no last_fetch_time. Fetching fallback...")
                    df_1h = self._get_cached_data('1h', mt5.TIMEFRAME_H1, 250, min_bars=200)

            # --- STATE: SWEEP_DETECTED ---
            elif self.strategy.state == 'SWEEP_DETECTED':
                await asyncio.sleep(60)  # Wait for 1M candle close
                df_1m = self._get_cached_data('1m', mt5.TIMEFRAME_M1, 10, min_bars=3)
                df_1h = self._get_cached_data('1h', mt5.TIMEFRAME_H1, 250, min_bars=200)

            # --- STATE MACHINE EXECUTION ---
            
            # IDLE: Establish range or look for sweeps
            if self.strategy.state == 'IDLE':
                # Try to establish range
                if df_1h is not None and self.strategy.range_high is None:
                    if self.strategy.analyze_1h_range(df_1h):
                        logger.info("Initial 1H Range Established.")
                
                # Look for sweeps
                if self.strategy.range_high is not None and df_5m is not None:
                    if df_1h is None:
                        logger.error("CRITICAL: df_1h is None in IDLE state, emergency fetching...")
                        df_1h = self._get_cached_data('1h', mt5.TIMEFRAME_H1, 250, min_bars=200)
                    
                    sweep_result = self.strategy.analyze_5m_sweep(
                        df_5m, 
                        self.strategy.range_high, 
                        self.strategy.range_low, 
                        self.strategy.range_start_time,
                        df_1h
                    )
                    
                    if sweep_result:
                        if sweep_result['type'] == 'SWEEP':
                            logger.info(f"✅ Sweep Confirmed! Dir: {sweep_result['direction']}")
                            self.strategy.state = 'SWEEP_DETECTED'
                            self.strategy.sweep_direction = sweep_result['direction']
                            self.strategy.order_block_high = sweep_result['ob_high']
                            self.strategy.order_block_low = sweep_result['ob_low']
                            self.strategy.sweep_wick_extreme = sweep_result.get('sweep_wick_extreme', 
                                sweep_result['ob_high'] if sweep_result['direction'] == 'SHORT' else sweep_result['ob_low'])
                            self.strategy.entry_count = 0
                            self.strategy.last_entry_time = None
                        elif sweep_result['type'] == 'INVALIDATE':
                            logger.warning("Range broken without valid sweep. Invalidating.")
                            self.strategy.invalidate_setup()

            # SWEEP_DETECTED: Look for entry
            elif self.strategy.state == 'SWEEP_DETECTED':
                if df_1m is not None:
                    entry_result = self.strategy.analyze_1m_entry(
                        df_1m, 
                        self.strategy.order_block_high, 
                        self.strategy.order_block_low, 
                        self.strategy.sweep_direction,
                        self.strategy.sweep_wick_extreme,
                        self.strategy.range_high,
                        self.strategy.range_low,
                        df_1h
                    )

                    if entry_result:
                        if entry_result['type'] == 'ENTRY':
                            logger.info(f"🚀 ENTRY SIGNAL: {entry_result['direction']}")
                            success = await self.execute_trade(entry_result)
                            
                            if success:
                                self.strategy.entry_count += 1
                                self.strategy.last_entry_time = datetime.now()  

                                logger.info(f"Trade #{self.strategy.entry_count} executed.")
                                
                                if self.strategy.entry_count >= self.strategy.MAX_ENTRIES:
                                    logger.info("Max entries reached. Resetting to IDLE.")
                                    self.strategy.state = 'IDLE'
                                    self.pos_manager.set_last_exit()
                            else:
                                logger.warning("Trade execution failed. Staying in SWEEP_DETECTED.")
                            
                        elif entry_result['type'] == 'INVALIDATE':
                            logger.warning("Entry confirmation failed. Invalidating setup.")
                            self.strategy.invalidate_setup()

            # INVALIDATED: Try to establish new range if we have data
            if self.strategy.state == 'INVALIDATED' and df_1h is not None:
                if self.strategy.analyze_1h_range(df_1h):
                    logger.info("Cooldown over. New Range Set. Resuming IDLE.")
                    # Reset anti-spam tracker when transitioning out of cooldown
                    self._last_cooldown_log = None

            # Always manage positions
            await self.manage_position()

        except Exception as e:
            logger.error(f"Loop error: {e}", exc_info=True)
            await asyncio.sleep(1)

    async def manage_position(self):
        """Manages open positions: Trailing Stop updates"""
        position = self.mt5.get_position(Config.SYMBOL)
        
        if not position:
            if self.pos_manager.active_position:
                logger.info("Position closed externally or by SL/TP. Clearing local state.")
                self.pos_manager.clear_position()
                await self.tg.send_message("⚠️ Position closed (SL/TP or external).")  
            return

        tick = self.mt5.get_tick(Config.SYMBOL)
        if not tick:
            return

        current_price = tick.ask if position.type == 0 else tick.bid
        
        action = self.pos_manager.update(position, tick, Config.SYMBOL)
        
        if action == 'CLOSE':
            reason = getattr(self.pos_manager, 'close_reason', "Stop Loss / Trail Hit")
            logger.info(f"Closing position: {reason}")
            await self.close_position(reason=reason)
            return

        if self.pos_manager.active_position:
            current_sl = position.sl
            calculated_sl = self.pos_manager.active_position['current_sl']
            state = self.pos_manager.active_position
            
            direction = "LONG" if position.type == 0 else "SHORT"
            entry_price = state['entry_price']
            
            threshold = 0.0001 * current_price 

            should_update = False
            
            if position.type == 0:  # LONG
                if calculated_sl > current_sl + threshold:
                    should_update = True
            elif position.type == 1:  # SHORT
                if calculated_sl < current_sl - threshold:
                    should_update = True

            if should_update:
                await self.send_modify_order(
                    ticket=position.ticket, 
                    new_sl=calculated_sl, 
                    new_tp=0.0,
                    direction=direction,
                    entry_price=entry_price,
                    current_price=current_price
                )

    async def send_modify_order(self, ticket, new_sl, new_tp, direction, entry_price, current_price):
        """Sends modify order to MT5"""
        req = self.mt5.build_modify_order(ticket, new_sl, tp=new_tp)
        if not req:
            logger.error("Failed to build modify order request")
            return

        result = self.mt5.execute_order(req)

        if result is None:
            logger.error(f"Modify order returned None. Last Error: {mt5.last_error()}")
            return
                
        if result.retcode == mt5.TRADE_RETCODE_DONE or result.retcode == 10009:
            if direction == 'LONG':
                profit_pts = new_sl - entry_price
            else:
                profit_pts = entry_price - new_sl
                
            logger.info(f"✅ Trailing Stop Updated: New SL = {new_sl} | Locked = {profit_pts:.2f}")
            await self.tg.send_trail_alert(direction, new_sl, current_price, profit_pts)
        else:
            err_msg = result.comment
            logger.error(f"❌ Failed to update SL: {err_msg}")

    async def close_position(self, reason="Manual"):
        """Close open position"""
        position = self.mt5.get_position(Config.SYMBOL)
        if not position:
            return
            
        order_type = mt5.ORDER_TYPE_SELL if position.type == 0 else mt5.ORDER_TYPE_BUY
        
        tick = mt5.symbol_info_tick(Config.SYMBOL)
        price = tick.bid if position.type == 0 else tick.ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": Config.SYMBOL,
            "volume": position.volume,
            "type": order_type,
            "position": position.ticket,
            "price": price,
            "deviation": 10,
            "magic": 234000,
            "comment": f"Close: {reason}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = self.mt5.execute_order(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"Position closed: {reason}")
            self.pos_manager.clear_position()
            await self.tg.send_message(f"🔒 Position Closed: {reason}")
        else:
            logger.error(f"Failed to close position: {getattr(result, 'comment', 'Unknown')}")

    def shutdown(self):
        logger.info("Shutting down agent...")
        self.running = False
        self.mt5.shutdown()
        self.db.close()
        
        if self.tg.app:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.tg.stop())
            else:
                loop.run_until_complete(self.tg.stop())
        logger.info("Agent stopped.")

if __name__ == "__main__":
    agent = TradingAgent()
    asyncio.run(agent.start())