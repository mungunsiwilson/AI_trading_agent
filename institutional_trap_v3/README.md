# Institutional Trap v3.0 - Trading Agent

A high-performance, low-latency automated trading agent implementing the "Institutional Trap v3.0" strategy. Now supports both **Binance Futures** and **Deriv Synthetic Indices** (including Volatility 25).

## Features

- **Dual Platform Support**: Trade on Binance Futures or Deriv synthetic indices
- **Symmetric Long/Short Strategy**: Full v3.0 "Reaction Time" model for both directions
- **Three-Layer Entry System**:
  - Layer 1: 50-period VWMA on 1h chart for trend filter
  - Layer 2: Sweep detection with delta spike (>2.5x avg) and absorption confirmation
  - Layer 3: Tick speed drop (>50%) + order book depth increase (>20%)
- **Intelligent Position Management**:
  - Initial stop: 1.5x ATR
  - Breakeven trigger at 1.0x ATR profit
  - Dynamic trailing stop (2.0x or 1.5x ATR based on momentum)
  - Time limit exit (configurable)
- **High Performance**:
  - Full async/await with asyncio
  - WebSocket streaming via aiohttp
  - Incremental indicator calculations
  - NumPy arrays for vectorized operations
  - orjson for fast JSON parsing
  - uvloop support for Unix systems

## Supported Instruments

### Deriv Synthetic Indices
- **Volatility 25** (`R_25`) - Default
- Volatility 10, 25, 50, 75, 100
- Crash/Boom indices
- Step Index, Range Break, etc.

### Binance Futures
- All perpetual futures contracts (BTCUSDT, ETHUSDT, etc.)

## Setup Instructions

### 1. Clone and Install Dependencies

```bash
cd institutional_trap_v3
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file and edit it:

```bash
cp .env.example .env
nano .env
```

#### For Deriv (Volatility 25):

```env
# Platform Selection
TRADING_PLATFORM=deriv

# Deriv Configuration
DERIV_APP_ID=1089
DERIV_SERVER=ws.binaryws.com

# Trading Configuration
SYMBOL=R_25
POSITION_SIZE_USD=100
TIME_LIMIT_MINUTES=240
MAX_POSITIONS=1
TRADING_MODE=BOTH

# Telegram Notifications
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

#### For Binance Futures:

```env
# Platform Selection
TRADING_PLATFORM=binance

# Binance Configuration
EXCHANGE_API_KEY=your_binance_api_key_here
EXCHANGE_SECRET_KEY=your_binance_secret_key_here
EXCHANGE_TESTNET=true

# Trading Configuration
SYMBOL=BTC/USDT:USDT
POSITION_SIZE_USD=100
TIME_LIMIT_MINUTES=240
MAX_POSITIONS=1
TRADING_MODE=BOTH

# Telegram Notifications
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 3. Get Your API Keys

#### For Deriv:
1. Go to [Deriv API Token page](https://app.deriv.com/account/api-token)
2. Create a new token with "Read" and "Trade" scopes
3. Use the App ID `1089` (public test app) or register your own at [Deriv API](https://developers.deriv.com/)

#### For Binance:
1. Go to [Binance API Management](https://www.binance.com/en/my/settings/api-management)
2. Create a new API key with "Enable Futures" permission
3. Set `EXCHANGE_TESTNET=true` for testing

#### For Telegram Bot:
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow instructions
3. Get your bot token and chat ID

### 4. Run the Bot

```bash
python main.py
```

## Project Structure

```
institutional_trap_v3/
├── main.py                 # Entry point with TradingAgent class
├── config.py               # Configuration with platform support
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── README.md               # This file
├── strategy/
│   ├── core.py             # Three-layer strategy logic
│   └── indicators.py       # VWMA, ATR, Delta calculations
├── execution/
│   ├── exchange_client.py  # Unified client for Binance & Deriv
│   └── position_manager.py # Trailing stop management
├── notification/
│   └── telegram_bot.py     # Async Telegram notifications
├── data/
│   ├── streams.py          # WebSocket handlers for both platforms
│   └── buffers.py          # Circular buffers for real-time data
└── utils/
    ├── logger.py           # Async logging setup
    └── helpers.py          # Utility functions
```

## Strategy Overview

### Long Entry Conditions
1. **Trend Filter**: Price > 50-period VWMA (1h)
2. **Sweep Detection**: New 10-period low with massive sell delta (< -2.5x avg)
3. **Absorption**: No new low for 1-3 bars + flat/positive cumulative delta
4. **Micro Trigger**: Tick speed drops >50% AND bid depth increases >20%

### Short Entry Conditions
1. **Trend Filter**: Price < 50-period VWMA (1h)
2. **Sweep Detection**: New 10-period high with massive buy delta (> +2.5x avg)
3. **Absorption**: No new high for 1-3 bars + flat/negative cumulative delta
4. **Micro Trigger**: Tick speed drops >50% AND ask depth increases >20%

### Position Management
- **Initial Stop**: Entry ± (1.5 × ATR)
- **Breakeven**: Move to entry when price moves 1.0 × ATR in profit
- **Trailing Stop**: 
  - Strong momentum: 2.0 × ATR from extreme
  - Weak momentum: 1.5 × ATR from extreme
- **Time Exit**: Close after 240 minutes (configurable)

## Important Notes for Deriv Trading (Volatility 25)

### ⚠️ Signal Mode Only

**The bot operates in SIGNAL MODE for Deriv synthetic indices:**

1. **No Automatic Execution**: Deriv doesn't support market orders for synthetic indices via API. The bot will:
   - ✅ Monitor Volatility 25 (R_25) in real-time
   - ✅ Calculate all indicators (VWMA, ATR, Delta)
   - ✅ Detect sweep + absorption patterns
   - ✅ Send Telegram alerts with entry signals
   - ❌ NOT execute trades automatically

2. **Manual Trade Execution**: When you receive a signal alert on Telegram, you must manually execute the trade on the Deriv platform using the provided entry price, stop loss, and take profit levels.

3. **Signal Alert Format**:
   ```
   🚨 ENTRY SIGNAL - Volatility 25
   
   Direction: LONG
   Entry Price: 785.42
   Stop Loss: 780.15 (1.5x ATR)
   Take Profit: Open (trailing stop)
   
   Strategy: Institutional Trap v3.0
   Confidence: High
   Time: 2024-01-15 14:30:00 UTC
   ```

### Why Signal Mode?

Deriv's API for synthetic indices has limitations:
- No direct market order execution
- No traditional position management
- Tick-based pricing instead of order book

The bot provides professional-grade signal generation while you handle execution manually through the Deriv web/mobile app.

### Future Enhancements

To enable automatic execution on Deriv, you would need:
- Integration with Deriv's contract purchase API (`buy_contract_for_account`)
- Implementation of limit order logic with slippage tolerance
- Position tracking in local state with manual sync
- WebSocket subscription to `proposal` and `buy` streams

## Troubleshooting

### Common Issues

**"Not connected to Deriv"**
- Check your internet connection
- Verify `DERIV_APP_ID` is valid
- Try `DERIV_SERVER=ws-test.binaryws.com` for testing

**"No signals generated"**
- Ensure you're receiving tick/candle data (check logs)
- Verify the symbol is correct (`R_25` for Volatility 25)
- Check if market conditions match strategy requirements

**Telegram notifications not working**
- Verify bot token is correct
- Ensure bot is added to the chat/group
- Check that chat ID is correct (use @userinfobot to get your ID)

## Performance Optimization

For maximum performance:

1. **Use uvloop** (already enabled by default on Unix):
   ```bash
   pip install uvloop
   ```

2. **Use orjson** for faster JSON:
   ```bash
   pip install orjson
   ```

3. **Run on a VPS** close to exchange servers:
   - For Deriv: AWS/GCP in Asia or Europe
   - For Binance: AWS Tokyo or Ireland

4. **Monitor resource usage**:
   ```bash
   python -m cProfile -o profile.stats main.py
   ```

## Disclaimer

⚠️ **Trading involves substantial risk of loss.** This software is provided "as is" for educational purposes only. Past performance does not guarantee future results. Always test thoroughly on a demo account before using real funds.

## License

MIT License - See LICENSE file for details.

## Support

For issues or questions:
1. Check the logs in `logs/` directory
2. Review strategy parameters in `config.py`
3. Test with small position sizes first
