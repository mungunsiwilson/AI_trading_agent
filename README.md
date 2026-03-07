# Institutional Trap v3.0

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

High-performance algorithmic trading agent implementing the **"Institutional Trap v3.0"** strategy - a symmetric "Reaction Time" model for detecting liquidity sweeps and trading reversals on perpetual futures markets.

## 🎯 Strategy Overview

The Institutional Trap v3.0 strategy identifies institutional liquidity grabs through a three-layer confirmation system:

### Layer 1: Macro Trend Filter
- Uses 50-period Volume-Weighted Moving Average (VWMA) on 1-hour chart
- Long entries only when price > VWMA
- Short entries only when price < VWMA

### Layer 2: Exhaustion Signal (The Setup)
- Detects sweep of 10-period highs/lows on 1-minute chart
- Confirms delta spike (>2.5x average absolute delta)
- Validates absorption via cumulative delta over 1-3 subsequent bars

### Layer 3: Micro-Structure Trigger (The Entry)
- Monitors tick speed drop (>50% reduction from sweep period)
- Confirms order book depth increase (>20% on relevant side)
- Executes market order when both conditions met

### Intelligent Position Management
- **Initial Stop Loss**: 1.5x ATR from entry
- **Breakeven Trigger**: Moves to entry when price moves 1.0x ATR in profit
- **Dynamic Trailing Stop**: 2.0x ATR (strong momentum) or 1.5x ATR (weak momentum)
- **Time Limit Exit**: Automatic close after configurable duration (default: 240 min)

## 📁 Project Structure

```
institutional_trap_v3/
├── main.py                 # Entry point, initializes agent and bot
├── config.py               # Configuration and environment variables
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── strategy/
│   ├── __init__.py
│   ├── core.py             # Core strategy logic (should_enter)
│   └── indicators.py       # VWMA, ATR, Delta calculations
├── execution/
│   ├── __init__.py
│   ├── exchange_client.py  # Async CCXT wrapper
│   └── position_manager.py # Position state and stop management
├── notification/
│   ├── __init__.py
│   └── telegram_bot.py     # Async Telegram notifications
├── data/
│   ├── __init__.py
│   ├── streams.py          # WebSocket stream handlers
│   └── buffers.py          # Circular buffers for real-time data
└── utils/
    ├── __init__.py
    ├── logger.py           # Async logging setup
    └── helpers.py          # Utility functions
```

## ⚡ Performance Features

- **Asynchronous I/O**: Full asyncio implementation with non-blocking operations
- **WebSocket Streaming**: Real-time data via Binance Futures WebSocket
- **Efficient Data Structures**: 
  - `collections.deque` with maxlen for O(1) rolling windows
  - Running sums for incremental indicator calculations
  - NumPy arrays for vectorized operations
- **Fast JSON Parsing**: Uses `orjson` for high-speed serialization
- **uvloop Support**: Drop-in replacement for asyncio event loop (Unix only)
- **Connection Pooling**: Reused aiohttp sessions for REST calls
- **Memory Efficient**: Only stores required historical data

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Binance Futures account (testnet recommended for testing)
- Telegram bot token and chat ID

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd institutional_trap_v3
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your credentials
```

### Configuration

Edit `.env` file with your settings:

```bash
# Exchange Configuration
EXCHANGE_API_KEY=your_binance_api_key
EXCHANGE_SECRET_KEY=your_binance_secret_key
EXCHANGE_TESTNET=true  # Set to false for production

# Trading Configuration
SYMBOL=BTC/USDT:USDT
POSITION_SIZE_USD=100
TIME_LIMIT_MINUTES=240
MAX_POSITIONS=1
TRADING_MODE=BOTH  # BOTH, LONG_ONLY, or SHORT_ONLY

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Running the Bot

```bash
python main.py
```

## 📱 Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Show welcome message and commands |
| `/status` | Display current position and PnL |
| `/balance` | Show account balance |
| `/stop` | Emergency stop (closes all positions) |
| `/help` | Show help information |

## 🔧 Strategy Parameters

Parameters can be adjusted in `config.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `VWMA_PERIOD_H1` | 50 | VWMA period on 1h chart |
| `DELTA_SWEEP_PERIOD_M1` | 10 | Period for sweep detection |
| `DELTA_SPIKE_MULTIPLIER` | 2.5 | Multiplier for delta spike |
| `DELTA_AVERAGE_PERIOD` | 20 | Period for delta average |
| `ATR_PERIOD` | 10 | ATR calculation period |
| `INITIAL_STOP_ATR_MULTIPLIER` | 1.5 | Initial stop loss multiplier |
| `BREAKEVEN_ATR_MULTIPLIER` | 1.0 | Distance to trigger breakeven |
| `TRAILING_STOP_ATR_MULTIPLIER_BASE` | 2.0 | Trailing stop (strong momentum) |
| `TRAILING_STOP_ATR_MULTIPLIER_WEAK` | 1.5 | Trailing stop (weak momentum) |
| `TICK_SPEED_DROP_THRESHOLD` | 0.5 | Tick speed drop threshold (50%) |
| `ORDERBOOK_DEPTH_INCREASE_THRESHOLD` | 0.2 | Order book depth increase (20%) |

## 🛡️ Risk Management

- **Maximum Positions**: Configurable limit on concurrent positions
- **Time-Based Exit**: Automatic position closure after time limit
- **Circuit Breaker**: Pauses trading after consecutive errors
- **Emergency Stop**: `/stop` command closes all positions immediately

## 📊 Monitoring

The bot provides comprehensive logging:
- Console output with colored levels
- All trades, entries, exits logged
- Position updates and stop adjustments
- Error tracking and alerts

## 🐳 Docker Deployment (Optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

Build and run:
```bash
docker build -t institutional-trap-v3 .
docker run -d --env-file .env institutional-trap-v3
```

## 📈 Additional Optimizations

For further performance improvements:

1. **uvloop** (already included): Provides 2-4x asyncio performance on Unix
   ```bash
   pip install uvloop
   ```

2. **Pyroscope** for profiling:
   ```bash
   pip install pyroscope-io
   ```
   Add to main.py:
   ```python
   import pyroscope
   pyroscope.configure(
       application_name="institutional_trap_v3",
       server_address="http://localhost:4040"
   )
   ```

3. **Redis** for state persistence:
   ```bash
   pip install redis aiofiles
   ```
   Useful for crash recovery and multi-instance deployments.

4. **Numba** for hot loops (if needed):
   ```bash
   pip install numba
   ```

## ⚠️ Disclaimer

**Trading cryptocurrencies involves substantial risk of loss. This software is provided "as is" without warranty of any kind. Past performance does not guarantee future results. Only trade with capital you can afford to lose.**

- Test thoroughly on testnet before using real funds
- Monitor the bot regularly
- Be prepared to intervene manually if needed
- Understand the strategy fully before deploying

## 📝 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Support

For issues and questions, please open an issue on the repository.
