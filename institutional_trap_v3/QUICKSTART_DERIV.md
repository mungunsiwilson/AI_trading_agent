# Quick Start Guide - Deriv Volatility 25

## 🚀 Get Started in 5 Minutes

### Step 1: Set Up Environment

The project is already configured for Deriv Volatility 25. Just update your Telegram credentials:

```bash
cd /workspace/institutional_trap_v3
nano .env
```

Update these two values:
```env
TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
TELEGRAM_CHAT_ID=your_actual_chat_id_here
```

### Step 2: Install Dependencies (if not already done)

```bash
pip install -r requirements.txt
```

### Step 3: Run the Bot

```bash
python main.py
```

## 📱 What You'll Receive on Telegram

When the bot detects a setup, you'll get an alert like this:

```
🚨 ENTRY SIGNAL - Volatility 25 (R_25)

━━━━━━━━━━━━━━━━━━━━
Direction: LONG 📈
Entry Price: 785.42
Stop Loss: 780.15 (-0.67%)
Take Profit: Open (trailing)
━━━━━━━━━━━━━━━━━━━━

Strategy: Institutional Trap v3.0
Confidence: High (80%)
Time: 2024-01-15 14:30:00 UTC

💡 Action Required:
Manually execute this trade on Deriv platform
```

## 🎯 How to Trade the Signals

### When You Receive a LONG Signal:

1. **Open Deriv App/Website**
   - Go to [Deriv Trader](https://app.deriv.com/trader)
   - Select "Volatility 25 (1s)" index

2. **Execute the Trade**
   - Click "Buy" (for LONG signals)
   - Set your stake amount (e.g., $100)
   - Optionally set stop loss at the provided level

3. **Monitor the Trade**
   - The bot will send exit alerts when:
     - Stop loss is hit
     - Time limit reached (240 min default)
     - Trailing stop triggered

### When You Receive a SHORT Signal:

1. **Open Deriv App/Website**
2. **Click "Sell"** (for SHORT signals)
3. **Set stake and execute**
4. **Monitor for exit alerts**

## ⚙️ Configuration Options

### Change Symbol

Edit `.env` to trade other Deriv indices:
```env
SYMBOL=R_10    # Volatility 10
SYMBOL=R_25    # Volatility 25 (default)
SYMBOL=R_50    # Volatility 50
SYMBOL=R_75    # Volatility 75
SYMBOL=R_100   # Volatility 100
```

### Adjust Position Size

```env
POSITION_SIZE_USD=50    # Trade with $50 per signal
POSITION_SIZE_USD=200   # Trade with $200 per signal
```

### Change Trading Mode

```env
TRADING_MODE=BOTH        # Long and short signals (default)
TRADING_MODE=LONG_ONLY   # Only long signals
TRADING_MODE=SHORT_ONLY  # Only short signals
```

### Adjust Time Limit

```env
TIME_LIMIT_MINUTES=120   # Close trades after 2 hours
TIME_LIMIT_MINUTES=480   # Close trades after 8 hours
```

## 📊 Bot Commands

Send these commands to your bot on Telegram:

- `/start` - Start the bot
- `/status` - Check current position status
- `/balance` - Get account balance info
- `/stop` - Emergency stop (closes all positions)
- `/help` - Show help message

## 🔍 Understanding the Strategy

The bot looks for **institutional trap setups**:

### LONG Setup Example:
1. **Trend Filter**: Price is above 50-period VWMA (1h chart)
2. **Liquidity Sweep**: Price makes new 10-bar low with massive selling
3. **Absorption**: Selling stops, price doesn't make new low
4. **Entry Trigger**: Tick speed drops + bid depth increases
5. **Signal Sent**: You manually buy on Deriv

### Risk Management:
- **Initial Stop**: 1.5× ATR below entry
- **Breakeven**: Moves to entry when up 1.0× ATR
- **Trailing Stop**: Follows price at 2.0× ATR (or 1.5× if momentum weakens)
- **Time Exit**: Closes after 240 minutes if still open

## ⚠️ Important Reminders

1. **Signal Mode Only**: The bot sends alerts; YOU must execute trades manually
2. **Test First**: Use Deriv demo account before trading real money
3. **Start Small**: Begin with minimum position sizes
4. **Monitor**: Don't rely solely on the bot; watch your trades
5. **Risk Management**: Never risk more than you can afford to lose

## 🐛 Troubleshooting

### No Signals Received
- Check logs: `tail -f logs/institutional_trap.log`
- Verify symbol is correct (R_25)
- Ensure market conditions match strategy requirements
- Wait for proper setups (they may take hours/days)

### Bot Not Starting
- Check Telegram token format
- Verify internet connection
- Try test server: `DERIV_SERVER=ws-test.binaryws.com`

### Connection Issues
```bash
# Restart the bot
Ctrl+C  # Stop current instance
python main.py  # Start again
```

## 📈 Performance Tips

1. **Run on VPS**: Deploy on a server near Deriv's servers (Asia/Europe)
2. **Use Fast Internet**: Low latency = faster signal detection
3. **Keep Bot Running**: 24/7 operation catches all setups
4. **Monitor Logs**: Check for errors or warnings

## 🆘 Getting Help

If you encounter issues:

1. Check the logs in `logs/` directory
2. Review configuration in `.env`
3. Test with demo account first
4. Join trading communities for support

---

**Happy Trading! 🎯**

Remember: This is a tool to assist your trading, not a guaranteed profit machine. Always use proper risk management.
