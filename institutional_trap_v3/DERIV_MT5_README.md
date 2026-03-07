# Deriv MT5 Auto-Trading Bot - Quick Reference

## 🚀 What This Bot Does

**Automatic Trading on Deriv Volatility 25 (R_25) via MT5**

- ✅ **Detects** institutional trap setups in real-time
- ✅ **Analyzes** with machine learning (learns from every trade)
- ✅ **Executes** trades automatically through your MT5 terminal
- ✅ **Manages** positions with intelligent trailing stops
- ✅ **Alerts** you instantly via Telegram for every action
- ✅ **Improves** over time as ML model trains

---

## ⚡ Quick Start (Windows)

### 1. Copy Files to Windows PC
Copy the entire `institutional_trap_v3` folder to your Windows computer.

### 2. Install Python
Download from https://python.org (check "Add to PATH")

### 3. Open MT5 Terminal
- Login to your Deriv account
- Add R_25 to Market Watch

### 4. Setup Configuration
```cmd
cd institutionalal_trap_v3
copy .env.example .env
notepad .env
```

**Edit these in `.env`:**
```env
TELEGRAM_BOT_TOKEN=your_token_from_botfather
TELEGRAM_CHAT_ID=your_chat_id
MT5_ENABLED=true
SYMBOL=R_25
POSITION_SIZE_USD=100
```

### 5. Install Dependencies
```cmd
pip install -r requirements.txt
```

### 6. Run the Bot
Double-click `run_bot.bat` or:
```cmd
python main.py
```

---

## 📱 Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize bot |
| `/status` | Current position & strategy state |
| `/balance` | Account balance |
| `/ml` | ML performance analysis |
| `/stop` | Emergency stop (closes all positions) |
| `/help` | Show all commands |

---

## 🎯 How Automatic Execution Works

### Entry Process
1. Bot monitors R_25 price via WebSocket
2. Detects sweep + absorption pattern
3. Checks ML probability (>55% by default)
4. **Automatically sends market order to MT5**
5. Sends you Telegram alert with entry details

### Position Management
1. Sets initial stop loss at 1.5x ATR
2. Moves to breakeven at 1.0x ATR profit
3. Trails stop dynamically (2.0x or 1.5x ATR)
4. Closes automatically when stop hit or time limit reached
5. Records trade in database for ML training

### Learning Cycle
- **Trades 1-20**: Collecting data
- **Trade 20**: First ML model trained
- **Trades 21+**: ML filters low-probability setups
- **Every 10 trades**: Model retrains with new data

---

## 📊 Example Telegram Alerts

### Entry Alert
```
✅ ENTRY EXECUTED

Direction: LONG
Price: 1045.23
Size: 0.50
Stop Loss: 1038.45
ATR: 4.52
ML Probability: 72%
Ticket: 123456
```

### Exit Alert
```
🚪 POSITION CLOSED

Direction: LONG
Entry: 1045.23
Exit: 1052.67
PnL: $7.44 (+7.44%)
Reason: Trailing Stop Hit
```

### ML Analysis (`/ml` command)
```
🧠 ML Analysis Report

Total Trades: 47
Wins: 29 (61.7%)
Losses: 18
Total PnL: $142.35
Avg Win: $8.92
Avg Loss: -$5.23
Profit Factor: 2.14

Optimal Parameters:
Delta Spike: 3.2
Absorption Bars: 2.1
Tick Speed Drop: 58%
```

---

## ⚙️ Configuration Options

### Risk Settings (`.env`)
```env
# Position size per trade
POSITION_SIZE_USD=100

# Maximum concurrent positions
MAX_POSITIONS=1

# Close trade after X minutes
TIME_LIMIT_MINUTES=240

# ML minimum win probability to take trade
ML_MIN_PROBABILITY_THRESHOLD=0.55
```

### MT5 Settings (`.env`)
```env
# Enable auto-execution
MT5_ENABLED=true

# Optional: Auto-login to MT5
MT5_LOGIN=12345678
MT5_PASSWORD=your_password
MT5_SERVER=Deriv-Demo

# Order execution settings
MAGIC_NUMBER=123456
DEVIATION_POINTS=10
```

### Strategy Tuning (in `config.py`)
```python
DELTA_SPIKE_MULTIPLIER = 2.5    # Sensitivity to volume spikes
TICK_SPEED_DROP_THRESHOLD = 0.5 # 50% drop required
DEPTH_INCREASE_THRESHOLD = 0.2  # 20% depth increase required
```

---

## 🔍 Strategy Logic Summary

### Long Entry Conditions
1. **Trend Filter**: Price > 50 VWMA (1h chart)
2. **Sweep**: New 10-period low with massive sell delta (< -2.5x avg)
3. **Absorption**: No new low for 1-3 bars + flat/positive cumulative delta
4. **Trigger**: Tick speed drops 50% + bid depth increases 20%
5. **ML Check**: Win probability > threshold

### Short Entry Conditions (mirrored)
1. **Trend Filter**: Price < 50 VWMA (1h chart)
2. **Sweep**: New 10-period high with massive buy delta (> +2.5x avg)
3. **Absorption**: No new high for 1-3 bars + flat/negative cumulative delta
4. **Trigger**: Tick speed drops 50% + ask depth increases 20%
5. **ML Check**: Win probability > threshold

### Stop Loss Management
- **Initial**: Entry ± (1.5 × ATR)
- **Breakeven**: Move to entry at ± (1.0 × ATR) profit
- **Trailing**: Follows price at ± (2.0 × ATR), adjusts based on momentum

---

## 📁 File Structure

```
institutional_trap_v3/
├── main.py                 # Main bot entry point
├── config.py               # Configuration settings
├── .env                    # Your credentials (create this)
├── .env.example            # Template
├── run_bot.bat             # Windows launcher
├── requirements.txt        # Python dependencies
├── trades.db               # Trade history (auto-created)
├── ml_model.joblib         # ML model (auto-created after 20 trades)
├── logs/                   # Log files (auto-created)
├── strategy/
│   ├── core.py             # Strategy logic
│   └── indicators.py       # VWMA, ATR, Delta calculations
├── execution/
│   ├── mt5_client.py       # MT5 auto-execution
│   ├── position_manager.py # Stop loss management
│   └── trade_database.py   # Database + ML
├── data/
│   ├── streams.py          # WebSocket data feeds
│   └── buffers.py          # Real-time data buffers
└── notification/
    └── telegram_bot.py     # Telegram alerts
```

---

## 🛠️ Troubleshooting

### "MT5 initialization failed"
- Make sure MT5 terminal is running
- Verify you're logged into Deriv account
- Check R_25 is in Market Watch
- Try leaving MT5_LOGIN empty and login manually in MT5

### No trades being taken
- Wait for quality setups (can take hours/days)
- Check `/status` to see if already in a position
- Lower ML_MIN_PROBABILITY_THRESHOLD temporarily
- Ensure historical data loaded (wait 1-2 minutes after start)

### Bot won't start
- Check Python is installed and in PATH
- Verify `.env` file exists with valid Telegram credentials
- Run `pip install -r requirements.txt` again
- Check error messages in console

---

## 💡 Pro Tips

1. **Start on Demo**: Run for 50+ trades on demo before going live
2. **Monitor First Week**: Watch closely to understand behavior
3. **Adjust Gradually**: Change one parameter at a time
4. **Review ML Insights**: Use `/ml` command to find optimal settings
5. **Keep Logs**: Check `logs/` folder for detailed analysis
6. **VPS for 24/7**: Consider Windows VPS for uninterrupted trading

---

## 📈 Performance Tracking

The bot tracks everything in `trades.db`:
- Entry/exit prices and times
- PnL for each trade
- Strategy parameters at entry
- ML predictions vs actual outcomes
- Optimal parameter suggestions

View stats anytime with `/ml` command in Telegram.

---

## ⚠️ Important Warnings

- **High Risk**: Synthetic indices are extremely volatile
- **Demo First**: Always test on demo account initially
- **Not Financial Advice**: Use at your own risk
- **No Guarantees**: Past performance ≠ future results
- **ML Takes Time**: Needs 20+ trades to become effective

---

## 🎓 Learning More

The bot uses the **"Institutional Trap v3.0"** strategy based on:
- Liquidity sweeps and stop hunts
- Delta divergence and absorption
- Order flow microstructure
- Volume profile analysis

Read more about these concepts in trading literature on:
- Order flow trading
- Market microstructure
- Institutional footprint analysis
- Volume spread analysis

---

**Ready to start?** Follow the Quick Start guide above! 🚀
