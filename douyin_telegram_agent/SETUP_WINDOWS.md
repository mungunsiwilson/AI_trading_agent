# 🚀 Quick Setup Guide - Douyin Opportunity Finder

## ✅ System Status
Your system is **fully installed and tested**! It just needs your API keys to run with real data.

---

## 🔑 Step 1: Get Your FREE API Keys

### 1. Groq API Key (FREE - Required for AI scoring)
1. Go to https://console.groq.com/
2. Sign up / Log in
3. Click "API Keys" → "Create API Key"
4. Copy the key (starts with `gsk_...`)
5. **This is 100% FREE** with generous limits

### 2. TikHub API Key (Required for real Douyin data)
1. Go to https://tikhub.io/
2. Sign up / Log in
3. Get your API key from dashboard
4. **Note:** If you don't have this yet, the system runs in demo mode automatically

### 3. Telegram Bot Token (For sending reports)
1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Follow prompts to name your bot
4. Copy the token (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 4. Telegram Chat ID
**For personal chat:**
1. Message your new bot (click "Start")
2. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Look for `"chat":{"id":123456789,...}` - that number is your Chat ID

**For channel/group:**
1. Add your bot as an admin to the channel/group
2. Forward any message from the channel to **@getidsbot**
3. It will reply with the Chat ID (usually starts with `-100`)

---

## ⚙️ Step 2: Configure Your .env File

Edit the `.env` file in your project folder:

```bash
# Windows PowerShell:
notepad .env

# Or edit manually:
cd C:\Users\Mungunsi\Desktop\Projects\Market_analysis_AI_Agent\douyin_telegram_agent
```

Replace these lines with YOUR actual keys:

```env
# ✏️ REPLACE THIS WITH YOUR REAL KEY:
TIKHUB_API_KEY=your_actual_tikhub_key_here

# ✏️ REPLACE THIS WITH YOUR REAL KEY:
GROQ_API_KEY=gsk_your_actual_groq_key_here

# ✏️ REPLACE THESE WITH YOUR TELEGRAM INFO:
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789

# Set to true to send reports to Telegram:
ENABLE_TELEGRAM_REPORTS=true

# Optional: Set to false when using real API keys:
USE_DEMO_DATA=false
```

---

## ▶️ Step 3: Run the System

### Test Run (Demo Mode - No API Keys Needed)
```powershell
cd C:\Users\Mungunsi\Desktop\Projects\Market_analysis_AI_Agent\douyin_telegram_agent
$env:USE_DEMO_DATA="true"
python main.py
```

### Production Run (With Real API Keys)
```powershell
cd C:\Users\Mungunsi\Desktop\Projects\Market_analysis_AI_Agent\douyin_telegram_agent
python main.py
```

---

## 📊 What You'll Get

After running, check these files:

1. **Markdown Report:** `data/daily_report_YYYYMMDD.md`
2. **PDF Report:** `data/daily_report_YYYYMMDD.pdf`
3. **Logs:** `logs/scan.log`

If Telegram is configured, you'll also receive the PDF in your Telegram chat!

---

## ⏰ Daily Automation (Optional)

### Option A: Windows Task Scheduler
1. Open **Task Scheduler**
2. Create Basic Task → "Douyin Opportunity Finder"
3. Trigger: Daily at 9:00 AM
4. Action: Start a program
   - Program: `python.exe`
   - Arguments: `main.py`
   - Start in: `C:\Users\Mungunsi\Desktop\Projects\Market_analysis_AI_Agent\douyin_telegram_agent`

### Option B: Python Scheduler
```powershell
python scheduler.py
```
(Keeps running and executes daily at 9 AM China time)

---

## 🐛 Troubleshooting

### "Invalid API Key" errors
- Double-check you copied the entire key (no spaces)
- Make sure there are no quotes around the key in `.env`
- For Groq: Verify key starts with `gsk_`

### Telegram not receiving reports
- Verify bot token is correct (no extra spaces)
- Make sure you messaged the bot first (click "Start")
- For groups: Ensure bot has admin permissions

### Want to test without TikHub key?
Just run with demo mode:
```powershell
$env:USE_DEMO_DATA="true"
python main.py
```

---

## 📝 Example Output

```
============================================================
🚀 DOUYIN OPPORTUNITY FINDER
============================================================

[STEP 1/5] Fetching trending products from Douyin...
✓ Found 15 trending products

[STEP 2/5] Checking against TikTok Shop database...
✓ Identified 15 opportunity gaps

[STEP 3/5] Validating market potential...
✓ Validated 15 products

[STEP 4/5] Generating reports...
✓ Markdown report: data/daily_report_20260327.md
✓ PDF report: data/daily_report_20260327.pdf

[STEP 5/5] Sending report to Telegram...
✓ Report sent to Telegram!

============================================================
Pipeline Execution Summary
============================================================
Status: ✓ SUCCESS
Duration: 8.42 seconds
Products Found: 15
Gaps Identified: 15
Products Validated: 15
Report Generated: True
PDF Generated: True
Telegram Sent: True
============================================================
```

---

## 🎉 You're Ready!

Once you add your API keys to `.env`, just run:
```powershell
python main.py
```

And you'll get your daily Douyin opportunities report in Telegram! 📊
