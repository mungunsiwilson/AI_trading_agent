"""
Async exchange client supporting both Binance Futures and Deriv.
Handles all exchange interactions with retry logic and rate limiting.
"""

import asyncio
import time
from typing import Optional, Dict, Any, List
import logging

try:
    import orjson as json
except ImportError:
    import json

import aiohttp

from config import Config


logger = logging.getLogger("institutional_trap_v3")


class DerivClient:
    """
    Async Deriv API client using WebSocket.
    Deriv uses a single WebSocket connection for all operations.
    """
    
    def __init__(self, config: Config):
        """
        Initialize Deriv client.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._subscriptions: Dict[str, asyncio.Queue] = {}
        self._connected = False
        self._receive_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize Deriv WebSocket connection."""
        try:
            self._session = aiohttp.ClientSession()
            url = f"wss://{self.config.DERIV_SERVER}/websockets/v3?app_id={self.config.DERIV_APP_ID}"
            
            self._ws = await self._session.ws_connect(
                url,
                heartbeat=30,
                timeout=10
            )
            
            self._connected = True
            self._receive_task = asyncio.create_task(self._receive_messages())
            logger.info(f"Deriv connected to {self.config.DERIV_SERVER}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Deriv: {e}")
            raise
    
    async def _receive_messages(self) -> None:
        """Receive and route WebSocket messages."""
        try:
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._route_message(data)
                    except Exception as e:
                        logger.error(f"Error parsing Deriv message: {e}")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"Deriv WebSocket error: {self._ws.exception()}")
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.warning("Deriv WebSocket closed")
                    break
        except asyncio.CancelledError:
            pass
    
    async def _route_message(self, data: Dict[str, Any]) -> None:
        """Route message to pending request or subscription handler."""
        # Check if it's a response to a pending request
        req_id = data.get('req_id')
        if req_id and req_id in self._pending_requests:
            future = self._pending_requests.pop(req_id)
            if not future.done():
                if 'error' in data:
                    future.set_exception(Exception(data['error']['message']))
                else:
                    future.set_result(data)
            return
        
        # Check if it's a subscription update
        msg_type = data.get('msg_type')
        if msg_type and msg_type in self._subscriptions:
            queue = self._subscriptions[msg_type]
            await queue.put(data)
    
    async def _send_request(self, action: str, **params) -> Dict[str, Any]:
        """Send request and wait for response."""
        if not self._connected or not self._ws:
            raise Exception("Not connected to Deriv")
        
        self._request_id += 1
        req = {
            action: 1,
            "req_id": self._request_id,
            **params
        }
        
        future = asyncio.Future()
        self._pending_requests[self._request_id] = future
        
        await self._ws.send_json(req)
        
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self._pending_requests.pop(self._request_id, None)
            raise Exception(f"Request timeout for {action}")
    
    async def subscribe_ticks(self, symbol: str, queue: asyncio.Queue) -> None:
        """Subscribe to tick stream for symbol."""
        self._subscriptions['tick'] = queue
        req = {
            "ticks": symbol,
            "subscribe": 1,
            "req_id": self._request_id + 1
        }
        self._request_id += 1
        await self._ws.send_json(req)
    
    async def subscribe_candles(self, symbol: str, granularity: int, queue: asyncio.Queue) -> None:
        """Subscribe to candle stream. Granularity in seconds (60=1m, 3600=1h)."""
        self._subscriptions['candles'] = queue
        req = {
            "ohlc": symbol,
            "granularity": granularity,
            "subscribe": 1,
            "req_id": self._request_id + 1
        }
        self._request_id += 1
        await self._ws.send_json(req)
    
    async def fetch_ohlcv(self, symbol: str, granularity: int, count: int = 100) -> List[List[float]]:
        """Fetch historical OHLCV data."""
        response = await self._send_request(
            "ohlc",
            symbol=symbol,
            granularity=granularity,
            count=count
        )
        
        candles = []
        for ohlc in response.get('ohlc', {}).get('candles', []):
            candles.append([
                ohlc['open_time'],
                float(ohlc['open']),
                float(ohlc['high']),
                float(ohlc['low']),
                float(ohlc['close']),
                float(ohlc['volume'])
            ])
        
        return candles
    
    async def get_account_balance(self) -> Dict[str, Any]:
        """Get account balance."""
        response = await self._send_request("balance", account="current")
        return {
            'total': float(response.get('balance', {}).get('balance', 0)),
            'currency': response.get('balance', {}).get('currency', 'USD')
        }
    
    async def get_position_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current position info (for synthetic indices, we track locally)."""
        # Deriv synthetic indices don't have traditional positions via API
        # Position tracking is done locally in the trading agent
        return None
    
    async def close(self) -> None:
        """Close Deriv connection."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        if self._ws and not self._ws.closed:
            await self._ws.close()
        
        if self._session:
            await self._session.close()
        
        self._connected = False
        logger.info("Deriv connection closed")


class BinanceClient:
    """
    Async Binance Futures client using CCXT.
    """
    
    def __init__(self, config: Config):
        """
        Initialize Binance client.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.exchange = None
        self._initialized = False
        self._rate_limit_delay = 0.1
        self._last_request_time = 0.0
        self._error_count = 0
        self._max_errors = 5
        self._circuit_breaker = False
    
    async def initialize(self) -> None:
        """Initialize Binance connection."""
        try:
            import ccxt.async_support as ccxt
            
            self.exchange = ccxt.binanceusdm({
                'apiKey': self.config.EXCHANGE_API_KEY,
                'secret': self.config.EXCHANGE_SECRET_KEY,
                'sandbox': self.config.EXCHANGE_TESTNET,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',
                    'adjustForTimeDifference': True,
                }
            })
            
            await self.exchange.load_markets()
            self._initialized = True
            logger.info(f"Binance initialized (testnet={self.config.EXCHANGE_TESTNET})")
            
        except Exception as e:
            logger.error(f"Failed to initialize Binance: {e}")
            raise
    
    async def _rate_limit(self) -> None:
        """Apply rate limiting."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._rate_limit_delay:
            await asyncio.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time = time.time()
    
    async def _request_with_retry(self, func, *args, max_retries: int = 3, **kwargs) -> Any:
        """Execute request with retry logic."""
        if self._circuit_breaker:
            raise Exception("Circuit breaker is open")
        
        for attempt in range(max_retries):
            try:
                await self._rate_limit()
                result = await func(*args, **kwargs)
                self._error_count = 0
                return result
            except Exception as e:
                self._error_count += 1
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt == max_retries - 1:
                    if self._error_count >= self._max_errors:
                        self._circuit_breaker = True
                        logger.error("Circuit breaker activated due to consecutive errors")
                    raise
                
                await asyncio.sleep(0.1 * (2 ** attempt))
    
    async def fetch_balance(self) -> Dict[str, Any]:
        """Fetch account balance."""
        return await self._request_with_retry(self.exchange.fetch_balance)
    
    async def fetch_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch current position for symbol."""
        positions = await self._request_with_retry(
            self.exchange.fetch_positions,
            symbols=[symbol]
        )
        
        for pos in positions:
            if pos['symbol'] == symbol and float(pos['contracts']) != 0:
                return pos
        
        return None
    
    async def create_market_order(self, symbol: str, side: str, amount: float) -> Dict[str, Any]:
        """Create market order."""
        return await self._request_with_retry(
            self.exchange.create_order,
            symbol=symbol,
            type='market',
            side=side,
            amount=amount
        )
    
    async def close_position(self, symbol: str, position: Dict[str, Any]) -> Dict[str, Any]:
        """Close existing position."""
        contracts = abs(float(position['contracts']))
        side = 'sell' if position['side'] == 'long' else 'buy'
        
        return await self.create_market_order(symbol, side, contracts)
    
    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> List[List[float]]:
        """Fetch OHLCV data."""
        return await self._request_with_retry(
            self.exchange.fetch_ohlcv,
            symbol=symbol,
            timeframe=timeframe,
            limit=limit
        )
    
    def reset_circuit_breaker(self) -> None:
        """Reset circuit breaker."""
        self._circuit_breaker = False
        self._error_count = 0
    
    async def close(self) -> None:
        """Close Binance connection."""
        if self.exchange:
            await self.exchange.close()
            logger.info("Binance connection closed")


class ExchangeClient:
    """
    Unified exchange client that supports both Binance and Deriv.
    """
    
    def __init__(self, config: Config):
        """
        Initialize exchange client based on platform.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.platform = config.TRADING_PLATFORM
        self._client: Optional[DerivClient | BinanceClient] = None
    
    async def initialize(self) -> None:
        """Initialize exchange connection based on platform."""
        if self.platform == "deriv":
            self._client = DerivClient(self.config)
        else:
            self._client = BinanceClient(self.config)
        
        await self._client.initialize()
        logger.info(f"Exchange client initialized for platform: {self.platform}")
    
    async def fetch_balance(self) -> Dict[str, Any]:
        """Fetch account balance."""
        if isinstance(self._client, DerivClient):
            return await self._client.get_account_balance()
        return await self._client.fetch_balance()
    
    async def fetch_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch current position."""
        if isinstance(self._client, DerivClient):
            return await self._client.get_position_info(symbol)
        return await self._client.fetch_position(symbol)
    
    async def create_market_order(self, symbol: str, side: str, amount: float) -> Dict[str, Any]:
        """Create market order (only for Binance)."""
        if isinstance(self._client, DerivClient):
            raise NotImplementedError("Market orders not supported for Deriv synthetic indices")
        return await self._client.create_market_order(symbol, side, amount)
    
    async def close_position(self, symbol: str, position: Dict[str, Any]) -> Dict[str, Any]:
        """Close position (only for Binance)."""
        if isinstance(self._client, DerivClient):
            raise NotImplementedError("Position closing not supported for Deriv via API")
        return await self._client.close_position(symbol, position)
    
    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> List[List[float]]:
        """Fetch OHLCV data."""
        if isinstance(self._client, DerivClient):
            # Map timeframe to granularity
            granularity_map = {
                '1m': 60,
                '5m': 300,
                '15m': 900,
                '30m': 1800,
                '1h': 3600,
                '4h': 14400,
                '1d': 86400
            }
            granularity = granularity_map.get(timeframe, 60)
            return await self._client.fetch_ohlcv(symbol, granularity, limit)
        return await self._client.fetch_ohlcv(symbol, timeframe, limit)
    
    async def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol information (precision, limits)."""
        if isinstance(self._client, BinanceClient):
            if self._client.exchange and hasattr(self._client.exchange, 'markets'):
                market = self._client.exchange.markets.get(symbol)
                if market:
                    return {
                        'precision': {
                            'amount': market.get('precision', {}).get('amount', 0.001),
                            'price': market.get('precision', {}).get('price', 0.01),
                        },
                        'limits': {
                            'amount': market.get('limits', {}).get('amount', {}),
                        }
                    }
        # For Deriv, return default precision
        return {
            'precision': {
                'amount': 0.01,
                'price': 0.01,
            },
            'limits': {
                'amount': {'min': 0.01, 'max': 10000},
            }
        }
    
    async def subscribe_ticks(self, symbol: str, queue: asyncio.Queue) -> None:
        """Subscribe to tick stream (Deriv only)."""
        if isinstance(self._client, DerivClient):
            await self._client.subscribe_ticks(symbol, queue)
        else:
            raise NotImplementedError("Tick subscription only for Deriv")
    
    async def subscribe_candles(self, symbol: str, timeframe: str, queue: asyncio.Queue) -> None:
        """Subscribe to candle stream (Deriv only)."""
        if isinstance(self._client, DerivClient):
            granularity_map = {
                '1m': 60,
                '5m': 300,
                '15m': 900,
                '30m': 1800,
                '1h': 3600,
                '4h': 14400,
                '1d': 86400
            }
            granularity = granularity_map.get(timeframe, 60)
            await self._client.subscribe_candles(symbol, granularity, queue)
        else:
            raise NotImplementedError("Candle subscription only for Deriv")
    
    async def close(self) -> None:
        """Close exchange connection."""
        if self._client:
            await self._client.close()
