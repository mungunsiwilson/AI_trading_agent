# 🚀 Quick Start Guide (5 Minutes)

Get your Douyin Opportunity Finder running in 5 minutes!

## Step 1: Install Dependencies (1 min)

```bash
cd douyin_telegram_agent
pip install -r requirements.txt
```

## Step 2: Get FREE API Keys (2 mins)

### A. Groq API Key (FREE - Required for AI scoring)
1. Go to https://console.groq.com/
2. Sign up (free, no credit card needed)
3. Create API key
4. Copy the key (starts with `gsk_...`)

### B. TikHub API Key (Required for Douyin data)
1. Go to https://tikhub.io/
2. Sign up and get API key
3. Copy the key

### C. Telegram Bot (Free - For report delivery)
1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Name your bot (e.g., "Douyin Reports")
4. Copy the token

5. **Get Chat ID**:
   - Message your new bot
   - Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Find `"chat":{"id":123456789}`
   - Copy the number

## Step 3: Configure .env File (1 min)

```bash
cp .env.example .env
```

Edit `.env`:

```env
TIKHUB_API_KEY=your_tikhub_key_here
GROQ_API_KEY=gsk_your_groq_key_here
TELEGRAM_BOT_TOKEN=1234567890:AABBccDDeeFFggHHiiJJkkLLmmNNooP
TELEGRAM_CHAT_ID=123456789
ENABLE_TELEGRAM_REPORTS=true
```

## Step 4: Test Installation (30 sec)

```bash
python test_pipeline.py
```

Expected output:
```
✓ PASS: Imports
✓ PASS: Configuration
✓ PASS: Data Files
✓ PASS: Checker Agent
✓ PASS: Reporter Agent

Total: 5/5 tests passed
🎉 All tests passed! System is ready.
```

## Step 5: Run Pipeline (30 sec)

```bash
python main.py
```

This will:
1. Fetch trending products from Douyin
2. Find gaps (not on TikTok Shop US/UK)
3. Score each product using Groq AI
4. Generate PDF report
5. Send to your Telegram

Check outputs:
- `data/daily_report_YYYYMMDD.pdf` ← Your PDF report
- `logs/scan.log` ← Detailed logs

## Daily Automation

### Option A: Keep Running (Simplest)
```bash
python scheduler.py
```
Runs every day at 9 AM China time automatically.

### Option B: Windows Task Scheduler
1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at 1:00 AM
4. Action: `python.exe` 
   Arguments: `C:\path\douyin_telegram_agent\main.py`

### Option C: Mac/Linux Cron
```bash
crontab -e
# Add this line:
0 1 * * * TZ='Asia/Shanghai' cd /path/to/douyin_telegram_agent && python main.py
```

## Troubleshooting

### "No Groq API key"
→ Get free key at https://console.groq.com/
→ System works without it (rule-based scoring only)

### "TikHub API failed"
→ Check API key in .env
→ System uses cached data as fallback

### "Telegram not sending"
→ Verify bot token and chat ID
→ Make sure bot can message you (send it a message first)

### "Import errors"
→ Run: `pip install -r requirements.txt --upgrade`

## What's Next?

✅ System is now running!

Every morning at 9 AM China time, you'll receive:
- PDF report with top 20 opportunities
- Detailed analysis of top 10 products
- AI-generated content ideas for TikTok videos
- Market fit scores (1-10)

**Pro Tips:**
- Focus on products scored 8+ first
- Update TikTok CSV files weekly from Affiliate Center
- Check `logs/scan.log` if something seems off

---

**Need Help?**
- Full documentation: `README.md`
- Architecture details: `ARCHITECTURE.md`
- Logs: `logs/scan.log`
