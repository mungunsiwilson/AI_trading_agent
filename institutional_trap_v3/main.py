#!/usr/bin/env python3
"""
Institutional Trap v3.0 - Main Entry Point

High-performance algorithmic trading agent implementing the symmetric
"Reaction Time" model for both long and short positions.

Usage:
    python main.py

Requirements:
    - Python 3.10+
    - All dependencies from requirements.txt
    - Valid .env configuration file
"""

import asyncio
import signal
import sys
from typing import Optional, Dict, Any
import logging

# Try to use uvloop for better performance on Unix systems
try:
    import uvloop
    if sys.platform != "win32":
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        print("✓ Using uvloop for improved performance")
except ImportError:
    pass

from config import Config
from utils.logger import setup_logger
from utils.helpers import format_price, format_size, calculate_position_size
from strategy.core import StrategyCore, Direction, EntrySignal
from execution.exchange_client import ExchangeClient
from execution.position_manager import PositionManager, PositionAction
from execution.mt5_client import DerivMT5Client, OrderType
from execution.trade_database import TradeDatabase, StrategyOptimizer, TradeRecord
from notification.telegram_bot import TelegramBot
from data.streams import (
    TradeStream, OrderBookStream, MarkPriceStream, CandleStream,
    create_streams
)
from data.buffers import CircularBuffer


logger = logging.getLogger("institutional_trap_v3")


class TradingAgent:
    """
    Main trading agent orchestrating all components.
    Implements async event-driven architecture.
    """
    
    def __init__(self):
        """Initialize trading agent."""
        self.config = Config()
        self.logger = setup_logger(
            level=self.config.LOG_LEVEL,
            use_async=True
        )
        
        # Validate configuration
        errors = self.config.validate()
        if errors:
            for error in errors:
                self.logger.error(f"Configuration error: {error}")
            raise ValueError("Invalid configuration")
        
        # Components
        self.exchange: Optional[ExchangeClient] = None
        self.mt5_client: Optional[DerivMT5Client] = None  # For Deriv MT5 execution
        self.position_manager: Optional[PositionManager] = None
        self.telegram_bot: Optional[TelegramBot] = None
        self.strategy: Optional[StrategyCore] = None
        
        # Trade database and ML
        self.trade_db: Optional[TradeDatabase] = None
        self.ml_optimizer: Optional[StrategyOptimizer] = None
        self._trade_count_since_retrain = 0
        
        # Data queues
        self.trade_queue: asyncio.Queue = asyncio.Queue()
        self.orderbook_queue: asyncio.Queue = asyncio.Queue()
        self.mark_queue: asyncio.Queue = asyncio.Queue()
        self.candle_queue: asyncio.Queue = asyncio.Queue()
        
        # Streams
        self.streams: Dict[str, Any] = {}
        self._stream_tasks: list = []
        
        # State
        self._running = False
        self._symbol_info: Optional[Dict[str, Any]] = None
        self._current_atr: float = 0.0
        self._last_bar_delta: float = 0.0
        self._h1_candles_loaded = False
    
    async def initialize(self) -> None:
        """Initialize all components."""
        self.logger.info("Initializing Institutional Trap v3.0...")
        
        # Initialize trade database first
        self.trade_db = TradeDatabase("trades.db")
        self.logger.info("Trade database initialized")
        
        # Initialize ML optimizer if enabled
        if self.config.ML_ENABLED:
            self.ml_optimizer = StrategyOptimizer(
                self.trade_db, 
                "ml_model.joblib",
                min_trades_for_training=self.config.ML_MIN_TRADES_FOR_TRAINING
            )
            # Try to load existing model
            if self.ml_optimizer.load_model():
                self.logger.info("ML model loaded successfully")
            else:
                self.logger.info(f"No pre-trained ML model found (will train after {self.config.ML_MIN_TRADES_FOR_TRAINING} trades)")
        
        # Initialize exchange client
        self.exchange = ExchangeClient(self.config)
        await self.exchange.initialize()
        
        # Get symbol info for precision
        self._symbol_info = await self.exchange.get_symbol_info(
            self.config.get_symbol_for_ccxt()
        )
        
        # Initialize MT5 client for Deriv execution (Windows only)
        if self.config.TRADING_PLATFORM == "deriv" and self.config.MT5_ENABLED:
            self.mt5_client = DerivMT5Client(self.config)
            if await self.mt5_client.initialize():
                self.logger.info("MT5 client initialized - Automatic execution ENABLED")
            else:
                self.logger.warning("MT5 initialization failed - Falling back to signal mode")
                self.mt5_client = None
        else:
            self.mt5_client = None
        
        # Initialize position manager
        self.position_manager = PositionManager(self.config, self.exchange)
        
        # Initialize strategy
        self.strategy = StrategyCore(self.config)
        
        # Initialize Telegram bot
        self.telegram_bot = TelegramBot(self.config)
        await self.telegram_bot.initialize()
        
        # Set up callbacks
        self.telegram_bot.set_callbacks(
            get_status=self.get_status_message,
            get_balance=self.get_balance_message,
            stop_trading=self.emergency_stop,
            get_ml_analysis=self.get_ml_analysis,
            close_position=self.close_current_position
        )
        
        # Load historical data for indicators
        await self.load_historical_data()
        
        self.logger.info("Initialization complete")
    
    async def load_historical_data(self) -> None:
        """Load historical data to prime indicators."""
        self.logger.info("Loading historical data...")
        
        try:
            # Load 1-hour candles for VWMA
            h1_candles = await self.exchange.fetch_ohlcv(
                self.config.get_symbol_for_ccxt(),
                timeframe='1h',
                limit=self.config.VWMA_PERIOD_H1 + 10
            )
            
            for candle in h1_candles:
                timestamp, open_p, high, low, close, volume = candle
                self.strategy.update_h1_candle(close, volume)
            
            self._h1_candles_loaded = True
            
            # Load 1-minute candles for ATR and Delta
            m1_candles = await self.exchange.fetch_ohlcv(
                self.config.get_symbol_for_ccxt(),
                timeframe='1m',
                limit=100
            )
            
            # Use m1_candles for the loop (was incorrectly using h1_candles[-100:])
            for candle in m1_candles:
                timestamp, open_p, high, low, close, volume = candle
                # Approximate delta as 0 for historical data
                self.strategy.update_m1_candle(
                    open_p, high, low, close, volume, 0, int(timestamp)
                )
            
            self._current_atr = self.strategy.get_atr()
            
            self.logger.info(
                f"Historical data loaded: VWMA={format_price(self.strategy._h1_vwma)}, "
                f"ATR={format_price(self._current_atr)}"
            )
            
        except Exception as e:
            self.logger.error(f"Error loading historical data: {e}")
            raise
    
    async def start_streams(self) -> None:
        """Start WebSocket data streams based on platform."""
        self.logger.info("Starting data streams...")
        
        # Create HTTP session for streams
        import aiohttp
        self._session = aiohttp.ClientSession()
        
        # Create streams based on platform
        if self.config.TRADING_PLATFORM == "deriv":
            # For Deriv, use the new stream classes
            from data.streams import DerivTickStream, DerivCandleStream
            
            symbol_clean = self.config.SYMBOL  # R_25 for Deriv
            
            self.streams['trades'] = DerivTickStream(
                symbol_clean, 
                self.trade_queue,
                self.config.DERIV_APP_ID,
                self.config.DERIV_SERVER
            )
            self.streams['candles_m1'] = DerivCandleStream(
                symbol_clean, 
                60,  # 1-minute granularity
                self.candle_queue,
                self.config.DERIV_APP_ID,
                self.config.DERIV_SERVER
            )
            self.streams['candles_h1'] = DerivCandleStream(
                symbol_clean, 
                3600,  # 1-hour granularity
                asyncio.Queue(),  # Separate queue for H1
                self.config.DERIV_APP_ID,
                self.config.DERIV_SERVER
            )
            
            self.logger.info(f"Started Deriv streams for {symbol_clean}")
        else:
            # For Binance
            symbol_clean = self.config.SYMBOL.replace("/", "").replace(":USDT", "")
            
            self.streams['trades'] = TradeStream(symbol_clean, self.trade_queue)
            self.streams['orderbook'] = OrderBookStream(symbol_clean, self.orderbook_queue)
            self.streams['mark_price'] = MarkPriceStream(symbol_clean, self.mark_queue)
            self.streams['candles_m1'] = CandleStream(symbol_clean, '1m', self.candle_queue)
            self.streams['candles_h1'] = CandleStream(symbol_clean, '1h', self.candle_queue)
            
            self.logger.info(f"Started Binance streams for {symbol_clean}")
        
        # Start stream tasks
        for name, stream in self.streams.items():
            task = asyncio.create_task(stream.start(self._session))
            self._stream_tasks.append(task)
            self.logger.info(f"Started {name} stream")
    
    async def process_events(self) -> None:
        """Main event processing loop."""
        self.logger.info("Starting event processing loop...")
        
        while self._running:
            try:
                # Process queues with timeout
                await self.process_queues(timeout=0.1)
                
                # Check for entry signals (only if no position)
                if not self.position_manager.has_position() and self.strategy.is_ready():
                    signal = self.strategy.should_enter()
                    if signal:
                        await self.execute_entry(signal)
                
                # Update position management
                if self.position_manager.has_position():
                    await self.manage_position()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in event loop: {e}", exc_info=True)
                await asyncio.sleep(1)
    
    async def process_queues(self, timeout: float = 0.1) -> None:
        """Process data from all queues."""
        try:
            # Process trade queue
            while not self.trade_queue.empty():
                trade = await asyncio.wait_for(self.trade_queue.get(), timeout=0.01)
                self.handle_trade(trade)
        except (asyncio.TimeoutError, asyncio.QueueEmpty):
            pass
        
        try:
            # Process orderbook queue
            while not self.orderbook_queue.empty():
                orderbook = await asyncio.wait_for(self.orderbook_queue.get(), timeout=0.01)
                self.handle_orderbook(orderbook)
        except (asyncio.TimeoutError, asyncio.QueueEmpty):
            pass
        
        try:
            # Process mark price queue
            while not self.mark_queue.empty():
                mark = await asyncio.wait_for(self.mark_queue.get(), timeout=0.01)
                self.handle_mark_price(mark)
        except (asyncio.TimeoutError, asyncio.QueueEmpty):
            pass
        
        try:
            # Process candle queue
            while not self.candle_queue.empty():
                candle = await asyncio.wait_for(self.candle_queue.get(), timeout=0.01)
                await self.handle_candle(candle)
        except (asyncio.TimeoutError, asyncio.QueueEmpty):
            pass
    
    def handle_trade(self, trade: Dict[str, Any]) -> None:
        """Handle incoming trade."""
        if trade.get('type') != 'trade':
            return
        
        self.strategy.add_trade(
            price=trade['price'],
            size=trade['size'],
            side=trade['side'],
            timestamp=trade['timestamp']
        )
    
    def handle_orderbook(self, orderbook: Dict[str, Any]) -> None:
        """Handle order book update."""
        if orderbook.get('type') != 'orderbook':
            return
        
        self.strategy.update_orderbook(
            bids=orderbook['bids'],
            asks=orderbook['asks']
        )
    
    def handle_mark_price(self, mark: Dict[str, Any]) -> None:
        """Handle mark price update."""
        if mark.get('type') != 'mark_price':
            return
        
        self.strategy.update_mark_price(mark['price'])
    
    async def handle_candle(self, candle: Dict[str, Any]) -> None:
        """Handle candle update."""
        if candle.get('type') != 'candle':
            return
        
        timeframe = candle.get('timeframe')
        
        if not candle.get('closed', False):
            return  # Only process closed candles
        
        if timeframe == '1h':
            # Update VWMA
            self.strategy.update_h1_candle(
                close=candle['close'],
                volume=candle['volume']
            )
        
        elif timeframe == '1m':
            # Finalize previous bar delta
            self._last_bar_delta = self.strategy.finalize_bar()
            
            # Update M1 bar data
            self.strategy.update_m1_candle(
                open_price=candle['open'],
                high=candle['high'],
                low=candle['low'],
                close=candle['close'],
                volume=candle['volume'],
                delta=self._last_bar_delta,
                timestamp=candle['timestamp']
            )
            
            # Update ATR
            self._current_atr = self.strategy.get_atr()
    
    async def execute_entry(self, signal: EntrySignal) -> None:
        """Execute entry order."""
        try:
            # Calculate position size
            contracts = calculate_position_size(
                self.config.POSITION_SIZE_USD,
                signal.entry_price
            )
            
            # Normalize to exchange precision
            if self._symbol_info:
                step_size = self._symbol_info.get('precision', {}).get('amount', 0.001)
                contracts = round(contracts / step_size) * step_size
            
            # Check ML recommendation if enabled
            should_take = True
            ml_probability = 0.5
            if self.ml_optimizer and self.config.ML_ENABLED:
                features = {
                    'vwma_1h': self.strategy._h1_vwma,
                    'atr_1m': self._current_atr,
                    'delta_spike': signal.delta_spike,
                    'absorption_bars': signal.absorption_bars,
                    'tick_speed_drop': signal.tick_speed_drop,
                    'orderbook_depth_change': signal.depth_change,
                    'direction': 'BUY' if signal.direction == Direction.LONG else 'SELL'
                }
                should_take, ml_probability = self.ml_optimizer.should_take_trade(
                    features, 
                    min_probability=self.config.ML_MIN_PROBABILITY_THRESHOLD
                )
                
                if not should_take:
                    self.logger.info(f"ML advised skipping trade (probability: {ml_probability:.2%})")
                    await self.telegram_bot.send_message(
                        f"⚠️ Trade SKIPPED by ML\n\n"
                        f"Direction: {signal.direction.name}\n"
                        f"Probability: {ml_probability:.2%}\n"
                        f"Threshold: {self.config.ML_MIN_PROBABILITY_THRESHOLD:.2%}"
                    )
                    return
            
            side = 'buy' if signal.direction == Direction.LONG else 'sell'
            direction_int = 1 if signal.direction == Direction.LONG else -1
            
            # Execute via MT5 for Deriv, or CCXT for Binance
            if self.mt5_client and self.config.TRADING_PLATFORM == "deriv":
                # MT5 execution
                mt5_direction = OrderType.BUY if signal.direction == Direction.LONG else OrderType.SELL
                result = await self.mt5_client.execute_market_order(mt5_direction, contracts)
                
                if not result.success:
                    raise Exception(f"MT5 order failed: {result.message}")
                
                ticket = result.ticket
                entry_price = result.price
                self.logger.info(f"MT5 order executed: Ticket {ticket}, Price {entry_price}")
            else:
                # CCXT execution (Binance or fallback)
                self.logger.info(
                    f"Placing {side} order: {contracts} contracts @ {signal.entry_price}"
                )
                
                order = await self.exchange.create_market_order(
                    self.config.get_symbol_for_ccxt(),
                    side,
                    contracts
                )
                
                ticket = order.get('id', 0)
                entry_price = signal.entry_price
            
            # Open position in manager
            self.position_manager.open_position(
                direction=direction_int,
                entry_price=entry_price,
                contracts=contracts,
                atr=self._current_atr
            )
            
            # Store entry context for later trade recording
            self._pending_trade = {
                'ticket': ticket,
                'symbol': self.config.SYMBOL,
                'direction': 'BUY' if signal.direction == Direction.LONG else 'SELL',
                'entry_price': entry_price,
                'volume': contracts,
                'entry_time': asyncio.get_event_loop().time(),
                'stop_loss': self.position_manager.get_current_stop(),
                'vwma_1h': self.strategy._h1_vwma,
                'atr_1m': self._current_atr,
                'delta_spike': signal.delta_spike,
                'absorption_bars': signal.absorption_bars,
                'tick_speed_drop': signal.tick_speed_drop,
                'orderbook_depth_change': signal.depth_change,
                'ml_probability': ml_probability
            }
            
            # Send notification
            msg = (
                f"✅ <b>ENTRY EXECUTED</b>\n\n"
                f"Direction: {signal.direction.name}\n"
                f"Price: {entry_price:.4f}\n"
                f"Size: {contracts}\n"
                f"Stop Loss: {self.position_manager.get_current_stop():.4f}\n"
                f"ATR: {self._current_atr:.4f}\n"
                f"ML Probability: {ml_probability:.2%}\n"
                f"Ticket: {ticket}"
            )
            await self.telegram_bot.send_message(msg)
            
            self.logger.info(f"Entry executed: {signal.direction.name} @ {entry_price}, Ticket: {ticket}")
            
        except Exception as e:
            self.logger.error(f"Entry execution failed: {e}", exc_info=True)
            await self.telegram_bot.send_error_notification(f"Entry failed: {e}")
    
    async def manage_position(self) -> None:
        """Manage active position."""
        current_price = self.strategy._current_mark_price
        
        if current_price <= 0:
            return
        
        # Check stop loss hit
        if self.position_manager.check_stop_loss(current_price):
            await self.exit_position("Stop Loss Hit")
            return
        
        # Update trailing stop
        action, new_stop = self.position_manager.update(
            current_price=current_price,
            current_delta=self._last_bar_delta
        )
        
        if action == PositionAction.EXIT:
            await self.exit_position("Time Limit Reached")
        elif action == PositionAction.UPDATE_STOP:
            self.logger.debug(f"Stop updated to {new_stop:.2f}")
    
    async def exit_position(self, reason: str) -> None:
        """Exit current position."""
        try:
            pos_info = self.position_manager.get_position_info()
            if not pos_info:
                return
            
            entry_price = pos_info['entry_price']
            direction = pos_info['direction']
            
            # Close via exchange/MT5
            if self.mt5_client and self.config.TRADING_PLATFORM == "deriv":
                # Get MT5 position ticket
                mt5_positions = await self.mt5_client.get_open_positions()
                if mt5_positions:
                    # Close the most recent position for our symbol
                    for pos in mt5_positions:
                        if pos.symbol == self.config.SYMBOL:
                            result = await self.mt5_client.close_position(pos.ticket)
                            if result.success:
                                self.logger.info(f"MT5 position closed: Ticket {pos.ticket}")
                            break
            else:
                result = await self.position_manager.close_position()
            
            # Calculate PnL
            current_price = self.strategy._current_mark_price
            pnl = self.position_manager.get_unrealized_pnl(current_price)
            
            # Record trade in database
            if hasattr(self, '_pending_trade') and self._pending_trade:
                from datetime import datetime
                trade_record = TradeRecord(
                    ticket=self._pending_trade['ticket'],
                    symbol=self._pending_trade['symbol'],
                    direction=self._pending_trade['direction'],
                    entry_price=self._pending_trade['entry_price'],
                    exit_price=current_price,
                    volume=self._pending_trade['volume'],
                    entry_time=datetime.fromtimestamp(self._pending_trade['entry_time']),
                    exit_time=datetime.now(),
                    pnl=pnl,
                    pnl_percent=(pnl / self.config.POSITION_SIZE_USD) * 100,
                    stop_loss=self._pending_trade['stop_loss'],
                    take_profit=0.0,  # Not used in trailing stop strategy
                    exit_reason=reason,
                    vwma_1h=self._pending_trade['vwma_1h'],
                    atr_1m=self._pending_trade['atr_1m'],
                    delta_spike=self._pending_trade['delta_spike'],
                    absorption_bars=self._pending_trade['absorption_bars'],
                    tick_speed_drop=self._pending_trade['tick_speed_drop'],
                    orderbook_depth_change=self._pending_trade['orderbook_depth_change']
                )
                self.trade_db.save_trade(trade_record)
                
                # Increment trade counter for ML retraining
                self._trade_count_since_retrain += 1
                
                # Auto-retrain ML model if enough trades accumulated
                if (self.ml_optimizer and self.config.ML_AUTO_RETRAIN and 
                    self._trade_count_since_retrain >= self.config.ML_RETRAIN_EVERY_N_TRADES):
                    self.logger.info(f"Auto-retraining ML model after {self._trade_count_since_retrain} trades...")
                    if self.ml_optimizer.train_model():
                        self._trade_count_since_retrain = 0
                        await self.telegram_bot.send_message("🧠 ML model retrained successfully!")
                
                # Clear pending trade
                self._pending_trade = None
            
            # Send notification
            msg = (
                f"🚪 <b>POSITION CLOSED</b>\n\n"
                f"Direction: {direction}\n"
                f"Entry: {entry_price:.4f}\n"
                f"Exit: {current_price:.4f}\n"
                f"PnL: ${pnl:.2f} ({pnl/self.config.POSITION_SIZE_USD*100:+.2f}%)\n"
                f"Reason: {reason}"
            )
            await self.telegram_bot.send_message(msg)
            
            self.logger.info(f"Position exited: {reason}, PnL: {pnl:.2f} USDT")
            
        except Exception as e:
            self.logger.error(f"Exit failed: {e}", exc_info=True)
            await self.telegram_bot.send_error_notification(f"Exit failed: {e}")
    
    async def get_ml_analysis(self) -> str:
        """Get ML analysis and performance stats for Telegram"""
        if not self.ml_optimizer or not self.config.ML_ENABLED:
            return "ML is disabled"
        
        # Get performance stats
        stats = self.trade_db.get_performance_stats()
        
        if stats['total_trades'] == 0:
            return "📊 No trades recorded yet"
        
        # Get optimal parameters
        optimal = self.ml_optimizer.get_optimal_parameters()
        
        msg = (
            f"🧠 <b>ML Analysis Report</b>\n\n"
            f"Total Trades: {stats['total_trades']}\n"
            f"Wins: {stats['wins']} ({stats['win_rate']:.1f}%)\n"
            f"Losses: {stats['losses']}\n"
            f"Total PnL: ${stats['total_pnl']:.2f}\n"
            f"Avg Win: ${stats['avg_win']:.2f}\n"
            f"Avg Loss: ${stats['avg_loss']:.2f}\n"
            f"Profit Factor: {stats['profit_factor']:.2f}\n"
        )
        
        if optimal:
            msg += (
                f"\n<b>Optimal Parameters:</b>\n"
                f"Delta Spike: {optimal.get('optimal_delta_spike', 'N/A'):.2f}\n"
                f"Absorption Bars: {optimal.get('optimal_absorption_bars', 'N/A'):.1f}\n"
                f"Tick Speed Drop: {optimal.get('optimal_tick_speed_drop', 'N/A'):.1%}\n"
            )
        
        return msg
    
    async def emergency_stop(self) -> None:
        """Emergency stop - close all positions and halt trading."""
        self.logger.warning("EMERGENCY STOP INITIATED")
        
        if self.position_manager.has_position():
            await self.exit_position("Emergency Stop")
        
        self._running = False
    
    async def close_current_position(self) -> str:
        """Close current position manually via Telegram command."""
        if not self.position_manager.has_position():
            return "📊 No open positions to close"
        
        try:
            pos = self.position_manager.get_position_info()
            await self.exit_position("Manual Close (Telegram)")
            
            return (
                f"✅ Position Closed Manually\n\n"
                f"Direction: {pos['direction']}\n"
                f"Entry: {pos['entry_price']:.2f}\n"
                f"Exit: {self.strategy._current_mark_price:.2f}"
            )
        except Exception as e:
            self.logger.error(f"Error closing position manually: {e}")
            return f"❌ Error closing position: {e}"
    
    async def get_status_message(self) -> str:
        """Get formatted status message for Telegram."""
        if not self.position_manager.has_position():
            return "📊 No open positions"
        
        pos = self.position_manager.get_position_info()
        current_price = self.strategy._current_mark_price
        pnl = self.position_manager.get_unrealized_pnl(current_price)
        pnl_sign = "+" if pnl >= 0 else ""
        
        elapsed_min = (int(asyncio.get_event_loop().time()) - pos['entry_time']) // 60
        
        return (
            f"📊 <b>Position Status</b>\n\n"
            f"Direction: {pos['direction']}\n"
            f"Entry: {pos['entry_price']:.2f}\n"
            f"Current: {current_price:.2f}\n"
            f"Stop: {pos['current_stop']:.2f}\n"
            f"PnL: {pnl_sign}{pnl:.2f} USDT\n"
            f"Duration: {elapsed_min} min"
        )
    
    async def get_balance_message(self) -> str:
        """Get formatted balance message for Telegram."""
        try:
            balance = await self.exchange.fetch_balance()
            total = balance.get('total', {})
            usdt = total.get('USDT', 0)
            
            return (
                f"💰 <b>Account Balance</b>\n\n"
                f"USDT: {usdt:.2f}"
            )
        except Exception as e:
            return f"Error fetching balance: {e}"
    
    async def run(self) -> None:
        """Run the trading agent."""
        try:
            self._running = True
            
            # Start Telegram bot
            await self.telegram_bot.start()
            
            # Start data streams
            await self.start_streams()
            
            # Give streams time to connect
            await asyncio.sleep(5)
            
            # Start main event loop
            await self.process_events()
            
        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
            await self.telegram_bot.send_error_notification(f"Fatal error: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self) -> None:
        """Graceful shutdown."""
        self.logger.info("Shutting down...")
        self._running = False
        
        # Close position if open
        if self.position_manager and self.position_manager.has_position():
            self.logger.info("Closing open position...")
            await self.position_manager.close_position()
        
        # Stop streams
        for task in self._stream_tasks:
            task.cancel()
        
        # Close session
        if hasattr(self, '_session'):
            await self._session.close()
        
        # Close exchange
        if self.exchange:
            await self.exchange.close()
        
        # Stop Telegram bot
        if self.telegram_bot:
            await self.telegram_bot.stop()
        
        self.logger.info("Shutdown complete")


async def main():
    """Main entry point."""
    agent: Optional[TradingAgent] = None
    
    def signal_handler(sig, frame):
        """Handle shutdown signals."""
        print("\nShutdown signal received...")
        if agent:
            asyncio.create_task(agent.shutdown())
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        agent = TradingAgent()
        await agent.initialize()
        await agent.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
