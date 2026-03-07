# Windows Setup Guide for Deriv MT5 Auto-Trading

## Complete Installation & Configuration Guide

This guide will help you set up the Institutional Trap v3.0 bot for **automatic trade execution** on Deriv Volatility 25 using MetaTrader 5 on Windows.

---

## 📋 Prerequisites

- Windows 10/11 PC
- Python 3.10 or higher
- Deriv MT5 terminal installed and logged in
- Deriv demo or live account with sufficient balance
- Telegram account (for notifications)

---

## 🔧 Step-by-Step Installation

### Step 1: Install Python

1. Download Python 3.10+ from https://www.python.org/downloads/windows/
2. Run the installer
3. ✅ **IMPORTANT**: Check "Add Python to PATH" during installation
4. Verify installation by opening Command Prompt and running:
   ```cmd
   python --version
   ```

### Step 2: Install Deriv MT5 Terminal

1. Go to https://www.deriv.com/en/trading-platforms/metatrader-5/
2. Download and install MT5 for Windows
3. Launch MT5 and login to your Deriv account (demo or real)
4. Add Volatility 25 (R_25) to Market Watch:
   - Right-click in Market Watch window
   - Select "Symbols"
   - Find "Synthetic Indices" → "Volatility Indices"
   - Select "Volatility 25 Index" and click "Show"

### Step 3: Clone/Copy the Bot Files

Copy the entire `institutional_trap_v3` folder to your Windows PC, for example:
```
C:\Trading\institutional_trap_v3\
```

### Step 4: Install Dependencies

Open Command Prompt as Administrator and navigate to the bot folder:

```cmd
cd C:\Trading\institutional_trap_v3
pip install -r requirements.txt
```

This will install all required packages including:
- `MetaTrader5` - For MT5 integration
- `pywin32` - Windows API support
- `aiohttp`, `websockets` - Async networking
- `numpy`, `pandas` - Data processing
- `scikit-learn` - Machine learning
- `python-telegram-bot` - Telegram notifications
- And more...

### Step 5: Configure Environment Variables

1. Copy the example environment file:
   ```cmd
   copy .env.example .env
   ```

2. Edit `.env` file with Notepad or VS Code:

```env
# Platform Selection
TRADING_PLATFORM=deriv

# Deriv Configuration (already set correctly)
DERIV_APP_ID=1089
DERIV_SERVER=ws.binaryws.com

# MT5 Configuration - IMPORTANT FOR AUTO EXECUTION
MT5_ENABLED=true
# Leave MT5_LOGIN empty if you manually login to MT5 terminal
# Or fill in for auto-login:
MT5_LOGIN=your_mt5_login_number
MT5_PASSWORD=your_mt5_password
MT5_SERVER=Deriv-Demo
MAGIC_NUMBER=123456
DEVIATION_POINTS=10

# Machine Learning (enabled by default)
ML_ENABLED=true
ML_MIN_TRADES_FOR_TRAINING=20
ML_MIN_PROBABILITY_THRESHOLD=0.55
ML_AUTO_RETRAIN=true
ML_RETRAIN_EVERY_N_TRADES=10

# Trading Configuration
SYMBOL=R_25
POSITION_SIZE_USD=100
TIME_LIMIT_MINUTES=240
MAX_POSITIONS=1
TRADING_MODE=BOTH

# Telegram Notifications - REQUIRED
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Logging
LOG_LEVEL=INFO
```

### Step 6: Set Up Telegram Bot

1. Open Telegram and search for @BotFather
2. Send `/newbot` command
3. Follow instructions to create your bot
4. Copy the bot token (looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)
5. Paste it in `.env` as `TELEGRAM_BOT_TOKEN`

6. Get your Chat ID:
   - Search for @userinfobot in Telegram
   - Start a chat and send any message
   - It will reply with your Chat ID
   - Paste it in `.env` as `TELEGRAM_CHAT_ID`

7. **Important**: Start a chat with your new bot and send `/start` to activate it

---

## 🚀 Running the Bot

### Option A: Direct Execution

```cmd
cd C:\Trading\institutional_trap_v3
python main.py
```

### Option B: Create a Batch File

Create `run_bot.bat` in the bot folder:

```batch
@echo off
echo Starting Institutional Trap v3.0 Bot...
cd /d %~dp0
python main.py
pause
```

Double-click `run_bot.bat` to start the bot.

### Option C: Run as Windows Service (Advanced)

Use NSSM (Non-Sucking Service Manager):

1. Download NSSM from https://nssm.cc/download
2. Extract and open Command Prompt as Administrator
3. Navigate to nssm folder and run:
   ```cmd
   nssm install DerivTradingBot
   ```
4. In the GUI:
   - Path: `C:\Python310\python.exe`
   - Startup directory: `C:\Trading\institutional_trap_v3`
   - Arguments: `main.py`
5. Click "Install service"
6. Start the service:
   ```cmd
   nssm start DerivTradingBot
   ```

---

## 📊 How It Works

### Automatic Execution Flow

1. **Data Collection**: Bot connects to Deriv WebSocket for real-time price data
2. **Strategy Analysis**: Monitors for institutional trap setups (sweep + absorption)
3. **ML Filtering**: Checks if trade meets success probability threshold
4. **Auto Execution**: Sends order directly to MT5 terminal
5. **Position Management**: Automatically adjusts stop loss and closes positions
6. **Telegram Alerts**: Notifies you of every action in real-time

### What You'll See

When the bot detects a setup and takes a trade:

1. **Entry Alert** (immediate):
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

2. **Updates During Trade**:
   - Stop loss adjustments (when breakeven is hit or trailing stop moves)
   - Significant price movements

3. **Exit Alert**:
   ```
   🚪 POSITION CLOSED
   
   Direction: LONG
   Entry: 1045.23
   Exit: 1052.67
   PnL: $7.44 (+7.44%)
   Reason: Trailing Stop Hit
   ```

---

## 🎛️ Telegram Commands

Once running, use these commands in your Telegram chat with the bot:

- `/start` - Initialize bot connection
- `/status` - Current position and strategy state
- `/balance` - Account balance info
- `/ml` - ML model performance and optimal parameters
- `/stop` - Emergency stop (closes all positions)
- `/help` - Show all available commands

---

## 📈 Machine Learning Features

The bot learns from every trade:

1. **Initial Phase** (0-20 trades): Collects data, no ML filtering
2. **Training Phase** (20+ trades): Builds first ML model
3. **Optimization Phase** (ongoing): 
   - Filters trades below probability threshold
   - Retrains every 10 trades with new data
   - Identifies optimal parameter values

### ML Model Analyzes:
- VWMA trend strength
- ATR volatility levels
- Delta spike magnitude
- Absorption bar count
- Tick speed drop percentage
- Order book depth changes
- Direction bias (long vs short)

---

## ⚙️ Configuration Tuning

### Risk Management

Edit these in `.env`:

```env
# Conservative
POSITION_SIZE_USD=50
ML_MIN_PROBABILITY_THRESHOLD=0.65

# Moderate (default)
POSITION_SIZE_USD=100
ML_MIN_PROBABILITY_THRESHOLD=0.55

# Aggressive
POSITION_SIZE_USD=200
ML_MIN_PROBABILITY_THRESHOLD=0.50
```

### Strategy Parameters

In `config.py`, you can adjust:

```python
DELTA_SPIKE_MULTIPLIER = 2.5  # Lower = more signals, Higher = fewer but stronger
TICK_SPEED_DROP_THRESHOLD = 0.5  # 50% drop required
DEPTH_INCREASE_THRESHOLD = 0.2  # 20% depth increase required
ATR_STOP_MULTIPLIER_INITIAL = 1.5
ATR_STOP_MULTIPLIER_TRAILING = 2.0
```

---

## 🐛 Troubleshooting

### MT5 Connection Issues

**Error**: "MT5 initialization failed"

**Solutions**:
1. Ensure MT5 terminal is running
2. Check you're logged into Deriv account in MT5
3. Verify R_25 is visible in Market Watch
4. Try manual login in MT5 first, then leave `MT5_LOGIN` empty in `.env`

### No Trades Being Taken

**Possible causes**:
1. Strategy not detecting setups (normal - waits for high-quality signals)
2. ML filtering too aggressive (lower `ML_MIN_PROBABILITY_THRESHOLD`)
3. Not enough historical data loaded (wait for candles to load)
4. Already in a position (check `/status`)

### Telegram Not Receiving Messages

**Check**:
1. Bot token is correct in `.env`
2. Chat ID is correct
3. You sent `/start` to the bot
4. Bot is not blocked

### High CPU Usage

**Solutions**:
1. Reduce logging level to WARNING in `.env`
2. Close unnecessary applications
3. Consider running on a VPS instead of local machine

---

## 🖥️ Running on a VPS (Recommended for 24/7 Trading)

For continuous operation, consider a Windows VPS:

**Providers**:
- AWS EC2 (Windows Server)
- Azure Virtual Machines
- Contabo Windows VPS
- Vultr Windows instances

**Setup**:
1. Rent Windows VPS ($10-30/month)
2. Install Python and MT5 on VPS
3. Copy bot files via RDP
4. Configure and run as service

**Benefits**:
- 24/7 uptime even when your PC is off
- Faster connection to Deriv servers
- No internet/power interruptions

---

## 📝 Important Notes

⚠️ **Risk Warnings**:
- This bot trades synthetic indices which are highly volatile
- Always start with a demo account
- Never risk more than you can afford to lose
- Past performance doesn't guarantee future results
- ML model needs time to become effective (20+ trades)

✅ **Best Practices**:
1. Monitor the bot closely for the first week
2. Keep Telegram notifications enabled
3. Review trade history regularly (`trades.db`)
4. Adjust parameters based on ML recommendations
5. Use `/stop` command if something seems wrong

---

## 📞 Support

If you encounter issues:

1. Check logs in `logs/` folder
2. Review error messages in console
3. Verify all configuration settings
4. Test with smaller position sizes first

---

## 🎯 Next Steps After Installation

1. ✅ Run bot on **demo account** for at least 50 trades
2. 📊 Review ML analysis after 20 trades (`/ml` command)
3. 🔧 Fine-tune parameters based on performance
4. 💰 Once profitable, consider switching to live account
5. 📈 Scale position size gradually

**Happy Trading!** 🚀
