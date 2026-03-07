"""
WebSocket stream handlers for real-time data.
Uses aiohttp for async WebSocket connections with reconnection logic.
Parses messages with orjson for speed.
"""

import asyncio
import time
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime, timezone
import logging

try:
    import orjson as json
except ImportError:
    import json

import aiohttp


logger = logging.getLogger("institutional_trap_v3")


class BaseStream:
    """Base class for WebSocket streams with reconnection logic."""
    
    def __init__(
        self,
        url: str,
        queue: asyncio.Queue,
        reconnect_delay: float = 5.0,
        max_reconnect_delay: float = 60.0
    ):
        """
        Initialize base stream.
        
        Args:
            url: WebSocket URL
            queue: Queue to emit parsed data
            reconnect_delay: Initial reconnect delay in seconds
            max_reconnect_delay: Maximum reconnect delay
        """
        self.url = url
        self.queue = queue
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._running = False
        self._current_reconnect_delay = reconnect_delay
    
    async def start(self, session: aiohttp.ClientSession) -> None:
        """Start the stream connection."""
        self._session = session
        self._running = True
        
        while self._running:
            try:
                await self._connect()
                await self._listen()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stream error: {e}, reconnecting in {self._current_reconnect_delay}s")
                if self._running:
                    await asyncio.sleep(self._current_reconnect_delay)
                    # Exponential backoff
                    self._current_reconnect_delay = min(
                        self._current_reconnect_delay * 2,
                        self.max_reconnect_delay
                    )
    
    async def _connect(self) -> None:
        """Establish WebSocket connection."""
        self._ws = await self._session.ws_connect(
            self.url,
            heartbeat=30,  # Ping every 30 seconds
            timeout=10
        )
        self._current_reconnect_delay = self.reconnect_delay
        logger.info(f"Connected to {self.url}")
        
        # Subscribe to channels (override in subclass)
        await self._subscribe()
    
    async def _subscribe(self) -> None:
        """Send subscription message. Override in subclass."""
        pass
    
    async def _listen(self) -> None:
        """Listen for messages and parse them."""
        async for msg in self._ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    await self._handle_message(data)
                except Exception as e:
                    logger.error(f"Error parsing message: {e}")
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error(f"WebSocket error: {self._ws.exception()}")
                break
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                logger.warning("WebSocket closed")
                break
    
    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """Handle parsed message. Override in subclass."""
        await self.queue.put(data)
    
    async def stop(self) -> None:
        """Stop the stream."""
        self._running = False
        if self._ws and not self._ws.closed:
            await self._ws.close()


class TradeStream(BaseStream):
    """
    Real-time trade stream.
    Emits trade events with price, size, and side.
    """
    
    def __init__(
        self,
        symbol: str,
        queue: asyncio.Queue,
        exchange: str = "binanceusdm"
    ):
        """
        Initialize trade stream.
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            queue: Queue for trade data
            exchange: Exchange name
        """
        # Binance Futures WebSocket URL for trades
        symbol_lower = symbol.replace("/", "").replace(":USDT", "").lower()
        url = f"wss://fstream.binance.com/ws/{symbol_lower}@trade"
        
        super().__init__(url, queue)
        self.symbol = symbol
    
    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """Parse and emit trade data."""
        if 'e' in data and data['e'] == 'trade':
            trade = {
                'type': 'trade',
                'timestamp': data.get('T', int(time.time() * 1000)),
                'price': float(data.get('p', 0)),
                'size': float(data.get('q', 0)),
                'side': 'buy' if data.get('m', False) else 'sell',  # m=True means buyer is maker
                'trade_id': data.get('t'),
            }
            await self.queue.put(trade)


class OrderBookStream(BaseStream):
    """
    Real-time order book depth stream.
    Maintains top N levels of bids and asks.
    """
    
    def __init__(
        self,
        symbol: str,
        queue: asyncio.Queue,
        levels: int = 5,
        exchange: str = "binanceusdm"
    ):
        """
        Initialize order book stream.
        
        Args:
            symbol: Trading symbol
            queue: Queue for order book data
            levels: Number of levels to track
            exchange: Exchange name
        """
        symbol_lower = symbol.replace("/", "").replace(":USDT", "").lower()
        # Use depth@50ms for fastest updates, or depth@100ms for more stability
        url = f"wss://fstream.binance.com/ws/{symbol_lower}@depth{levels}@100ms"
        
        super().__init__(url, queue)
        self.symbol = symbol
        self.levels = levels
        self._bids: Dict[float, float] = {}
        self._asks: Dict[float, float] = {}
        self._last_update_id = 0
    
    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """Parse and emit order book update."""
        if 'bids' not in data or 'asks' not in data:
            return
        
        # Update bids
        for bid_price, bid_size in data.get('bids', []):
            price = float(bid_price)
            size = float(bid_size)
            if size == 0:
                self._bids.pop(price, None)
            else:
                self._bids[price] = size
        
        # Update asks
        for ask_price, ask_size in data.get('asks', []):
            price = float(ask_price)
            size = float(ask_size)
            if size == 0:
                self._asks.pop(price, None)
            else:
                self._asks[price] = size
        
        # Get top N levels
        sorted_bids = sorted(self._bids.items(), key=lambda x: x[0], reverse=True)[:self.levels]
        sorted_asks = sorted(self._asks.items(), key=lambda x: x[0])[:self.levels]
        
        orderbook = {
            'type': 'orderbook',
            'timestamp': int(time.time() * 1000),
            'bids': sorted_bids,
            'asks': sorted_asks,
            'bid_depth': sum(size for _, size in sorted_bids),
            'ask_depth': sum(size for _, size in sorted_asks),
        }
        
        await self.queue.put(orderbook)


class MarkPriceStream(BaseStream):
    """
    Real-time mark price stream.
    Used for position valuation and liquidation calculations.
    """
    
    def __init__(
        self,
        symbol: str,
        queue: asyncio.Queue,
        exchange: str = "binanceusdm"
    ):
        """
        Initialize mark price stream.
        
        Args:
            symbol: Trading symbol
            queue: Queue for mark price data
            exchange: Exchange name
        """
        symbol_lower = symbol.replace("/", "").replace(":USDT", "").lower()
        url = f"wss://fstream.binance.com/ws/{symbol_lower}@markPrice@1s"
        
        super().__init__(url, queue)
        self.symbol = symbol
    
    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """Parse and emit mark price data."""
        if 'e' in data and data['e'] == 'markPriceUpdate':
            mark_price = {
                'type': 'mark_price',
                'timestamp': data.get('T', int(time.time() * 1000)),
                'price': float(data.get('p', 0)),
                'index_price': float(data.get('i', 0)),
                'funding_rate': float(data.get('r', 0)),
                'next_funding_time': data.get('T', 0),
            }
            await self.queue.put(mark_price)


class CandleStream(BaseStream):
    """
    Real-time candlestick (kline) stream.
    Provides OHLCV data for specified timeframe.
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str,
        queue: asyncio.Queue,
        exchange: str = "binanceusdm"
    ):
        """
        Initialize candle stream.
        
        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe (e.g., '1m', '1h')
            queue: Queue for candle data
            exchange: Exchange name
        """
        symbol_lower = symbol.replace("/", "").replace(":USDT", "").lower()
        url = f"wss://fstream.binance.com/ws/{symbol_lower}@kline_{timeframe}"
        
        super().__init__(url, queue)
        self.symbol = symbol
        self.timeframe = timeframe
    
    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """Parse and emit candle data."""
        if 'k' not in data:
            return
        
        k = data['k']
        candle = {
            'type': 'candle',
            'timeframe': self.timeframe,
            'timestamp': k.get('t', 0),
            'open': float(k.get('o', 0)),
            'high': float(k.get('h', 0)),
            'low': float(k.get('l', 0)),
            'close': float(k.get('c', 0)),
            'volume': float(k.get('v', 0)),
            'closed': k.get('x', False),  # True when candle is closed
            'trades': k.get('n', 0),
        }
        await self.queue.put(candle)


class DerivTickStream(BaseStream):
    """
    Deriv tick stream for synthetic indices.
    Emits tick events with price and timestamp.
    """
    
    def __init__(
        self,
        symbol: str,
        queue: asyncio.Queue,
        app_id: str = "1089",
        server: str = "ws.binaryws.com"
    ):
        """
        Initialize Deriv tick stream.
        
        Args:
            symbol: Deriv symbol (e.g., R_25 for Volatility 25)
            queue: Queue for tick data
            app_id: Deriv app ID
            server: Deriv WebSocket server
        """
        url = f"wss://{server}/websockets/v3?app_id={app_id}"
        super().__init__(url, queue)
        self.symbol = symbol
        self.app_id = app_id
        self._request_id = 0
    
    async def _subscribe(self) -> None:
        """Subscribe to ticks."""
        self._request_id += 1
        subscribe_msg = {
            "ticks": self.symbol,
            "subscribe": 1,
            "req_id": self._request_id
        }
        await self._ws.send_json(subscribe_msg)
        logger.info(f"Subscribed to Deriv ticks for {self.symbol}")
    
    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """Parse and emit tick data."""
        msg_type = data.get('msg_type')
        
        if msg_type == 'tick':
            tick_data = data.get('tick', {})
            trade = {
                'type': 'trade',
                'timestamp': int(tick_data.get('epoch', int(time.time())) * 1000),
                'price': float(tick_data.get('quote', 0)),
                'size': 1.0,  # Deriv doesn't provide size for synthetic indices
                'side': 'buy',  # Assume buy for synthetic indices
                'trade_id': tick_data.get('id'),
            }
            await self.queue.put(trade)


class DerivCandleStream(BaseStream):
    """
    Deriv OHLC stream for synthetic indices.
    Provides candlestick data for specified granularity.
    """
    
    def __init__(
        self,
        symbol: str,
        granularity: int,
        queue: asyncio.Queue,
        app_id: str = "1089",
        server: str = "ws.binaryws.com"
    ):
        """
        Initialize Deriv candle stream.
        
        Args:
            symbol: Deriv symbol (e.g., R_25)
            granularity: Candle granularity in seconds (60=1m, 3600=1h)
            queue: Queue for candle data
            app_id: Deriv app ID
            server: Deriv WebSocket server
        """
        url = f"wss://{server}/websockets/v3?app_id={app_id}"
        super().__init__(url, queue)
        self.symbol = symbol
        self.granularity = granularity
        self.timeframe = self._granularity_to_timeframe(granularity)
        self._request_id = 0
    
    def _granularity_to_timeframe(self, granularity: int) -> str:
        """Convert granularity in seconds to timeframe string."""
        mapping = {
            60: '1m',
            300: '5m',
            900: '15m',
            1800: '30m',
            3600: '1h',
            7200: '2h',
            14400: '4h',
            86400: '1d'
        }
        return mapping.get(granularity, f'{granularity}s')
    
    async def _subscribe(self) -> None:
        """Subscribe to candles."""
        self._request_id += 1
        subscribe_msg = {
            "ohlc": self.symbol,
            "granularity": self.granularity,
            "subscribe": 1,
            "req_id": self._request_id
        }
        await self._ws.send_json(subscribe_msg)
        logger.info(f"Subscribed to Deriv candles for {self.symbol} ({self.granularity}s)")
    
    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """Parse and emit candle data."""
        msg_type = data.get('msg_type')
        
        if msg_type == 'ohlc':
            ohlc_data = data.get('ohlc', {})
            candle_data = ohlc_data.get('candles', [{}])[-1] if ohlc_data.get('candles') else {}
            
            if candle_data:
                candle = {
                    'type': 'candle',
                    'timeframe': self.timeframe,
                    'timestamp': int(candle_data.get('open_time', 0) * 1000),
                    'open': float(candle_data.get('open', 0)),
                    'high': float(candle_data.get('high', 0)),
                    'low': float(candle_data.get('low', 0)),
                    'close': float(candle_data.get('close', 0)),
                    'volume': float(candle_data.get('volume', 0)),
                    'closed': False,  # Stream provides updating candles
                }
                await self.queue.put(candle)


async def create_streams(
    symbol: str,
    trade_queue: asyncio.Queue,
    orderbook_queue: asyncio.Queue,
    mark_queue: asyncio.Queue,
    candle_queue: asyncio.Queue,
    timeframe: str = '1m',
    platform: str = 'binance',
    deriv_app_id: str = "1089",
    deriv_server: str = "ws.binaryws.com"
) -> Dict[str, BaseStream]:
    """
    Create all required stream instances based on platform.
    
    Args:
        symbol: Trading symbol
        trade_queue: Queue for trade data
        orderbook_queue: Queue for order book data
        mark_queue: Queue for mark price data
        candle_queue: Queue for candle data
        timeframe: Candle timeframe (for Binance)
        platform: Trading platform ('binance' or 'deriv')
        deriv_app_id: Deriv app ID (for Deriv platform)
        deriv_server: Deriv WebSocket server (for Deriv platform)
    
    Returns:
        Dictionary of stream instances
    """
    if platform == "deriv":
        # For Deriv, we use tick stream and candle stream with granularity
        streams = {
            'trades': DerivTickStream(symbol, trade_queue, deriv_app_id, deriv_server),
            'candles_m1': DerivCandleStream(symbol, 60, candle_queue, deriv_app_id, deriv_server),  # 1-minute
            'candles_h1': DerivCandleStream(symbol, 3600, asyncio.Queue(), deriv_app_id, deriv_server),  # 1-hour
        }
        logger.info(f"Created Deriv streams for {symbol}")
    else:
        # For Binance
        streams = {
            'trades': TradeStream(symbol, trade_queue),
            'orderbook': OrderBookStream(symbol, orderbook_queue),
            'mark_price': MarkPriceStream(symbol, mark_queue),
            'candles': CandleStream(symbol, timeframe, candle_queue),
        }
        logger.info(f"Created Binance streams for {symbol}")
    
    return streams
