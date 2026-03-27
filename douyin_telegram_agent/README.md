# 🚀 Douyin Opportunity Finder

An automated AI-powered system that finds trending products on Douyin (Chinese TikTok) not yet available on TikTok Shop US/UK, validates their market potential using Groq's free LLM, and delivers daily PDF reports directly to your Telegram.

## ✨ Features

- **📊 Douyin Trend Discovery**: Fetches top-selling products from Douyin via TikHub API
- **🔍 Gap Analysis**: Identifies products NOT yet on TikTok Shop US/UK using fuzzy matching
- **🧠 AI Validation**: Scores products 1-10 using Groq's FREE Llama 3.3 model
- **📱 Telegram Delivery**: Sends professional PDF reports to your Telegram channel/group
- **⏰ Automated Scheduling**: Runs daily at 9 AM China time
- **📈 Market Intelligence**: Analyzes competition, cultural fit, visual appeal, and price point

## 📋 Prerequisites

- Python 3.9+
- TikHub API key (https://tikhub.io/)
- Groq API key - **FREE** (https://console.groq.com/)
- Telegram Bot Token (via @BotFather)

## 🚀 Quick Start

### 1. Clone & Install

```bash
cd douyin_telegram_agent
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your keys:

```env
# Get from https://tikhub.io/
TIKHUB_API_KEY=your_tikhub_key_here

# Get FREE from https://console.groq.com/
GROQ_API_KEY=gsk_your_groq_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Telegram Setup (see below)
TELEGRAM_BOT_TOKEN=bot_token_from_botfather
TELEGRAM_CHAT_ID=your_chat_id_here

ENABLE_TELEGRAM_REPORTS=true
```

### 3. Setup Telegram Bot

1. **Create Bot**: Message [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot`
   - Follow prompts to name your bot
   - Copy the API token

2. **Get Chat ID**:
   - For **private chat**: Message your bot, then visit:
     `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
     Look for `"chat":{"id":123456789}`
   
   - For **channel/group**: 
     - Add bot as admin
     - Forward a message from channel to [@getidsbot](https://t.me/getidsbot)
     - Copy the ID (usually starts with `-100`)

3. **Test Connection**:
   ```bash
   python -c "from telegram_services import TelegramSender; s = TelegramSender('TOKEN', 'CHAT_ID'); print('OK' if s.test_connection() else 'FAIL')"
   ```

### 4. Run Pipeline

```bash
python main.py
```

Check generated reports in `data/` folder:
- `daily_report_YYYYMMDD.pdf` - Professional PDF report
- `daily_report_YYYYMMDD.md` - Markdown version

### 5. Enable Daily Automation

**Option A: Python Scheduler**
```bash
python scheduler.py
```
Keeps running and executes daily at 9 AM China time.

**Option B: Cron Job (Linux/Mac)**
```bash
crontab -e
# Add this line (runs at 9 AM Shanghai time):
0 1 * * * TZ='Asia/Shanghai' cd /path/to/douyin_telegram_agent && /usr/bin/python3 main.py >> logs/cron.log 2>&1
```

**Option C: Windows Task Scheduler**
- Create basic task
- Trigger: Daily at 1:00 AM (equivalent to 9 AM China time)
- Action: `python.exe` with argument `C:\path\to\main.py`

## 📁 Project Structure

```
douyin_telegram_agent/
├── main.py                 # Main pipeline orchestrator
├── scheduler.py            # Daily scheduling
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
├── config/
│   ├── __init__.py        # Config loader
│   └── config.yaml        # Agent settings
├── agents/
│   ├── douyin_scout.py    # TikHub API integration
│   ├── tiktok_checker.py  # Fuzzy matching vs TikTok Shop
│   ├── market_validator.py# Groq LLM scoring
│   └── reporter.py        # Report generation
├── reporting/
│   ├── __init__.py
│   └── pdf_generator.py   # PDF creation
├── telegram_services/
│   ├── __init__.py
│   └── telegram_sender.py # Telegram delivery
├── data/
│   ├── tiktok_products_us.csv  # US product database
│   └── tiktok_products_uk.csv  # UK product database
└── logs/
    └── scan.log           # Execution logs
```

## 🤖 How It Works

### Pipeline Flow

1. **DouyinScoutAgent** → Fetches 50 trending products from TikHub API
2. **TikTokCheckerAgent** → Translates Chinese titles, checks against US/UK databases (fuzzy match ≥0.8)
3. **MarketValidatorAgent** → Scores each gap product using Groq LLM on 5 dimensions:
   - Competition (fewer sellers = higher score)
   - Sentiment (Reddit/social buzz)
   - Cultural Fit (Western appeal)
   - Visual Appeal (video potential)
   - Price Point (ideal $10-50)
4. **ReporterAgent** → Generates markdown summary
5. **PDFGenerator** → Creates professional PDF report
6. **TelegramSender** → Delivers PDF + summary to Telegram

### Scoring System

Each product receives a 1-10 score:
- **8-10**: High priority - create content immediately
- **6-7.9**: Medium priority - research suppliers
- **<6**: Low priority - monitor trends

## 🔧 Configuration

### config.yaml

Adjust agent parameters:

```yaml
agents:
  douyin_scout:
    max_products: 50      # Products to fetch
    min_hot_count: 1000   # Minimum popularity
  
  tiktok_checker:
    similarity_threshold: 0.8  # Fuzzy match threshold
  
  market_validator:
    model: llama-3.3-70b-versatile  # Groq model
    temperature: 0.3       # LLM creativity
```

## 📊 Sample Output

### PDF Report Includes:
- Executive summary with key metrics
- Top 20 opportunities table
- Detailed analysis of top 10 products
- Score breakdowns (competition, sentiment, etc.)
- Content angle suggestions for TikTok videos
- Action items prioritized by score

### Telegram Message:
```
📊 Daily Opportunity Report Ready!

🎯 Found 23 gap products
⭐ Top pick: "LED Desk Organizer with Wireless Charging" (Score: 8.7/10)
🔥 5 high-potential products (8+)

See attached PDF for full details.
```

## 🛠️ Troubleshooting

### "No products fetched from Douyin"
- Check TikHub API key is valid
- Verify internet connection
- Check `logs/scan.log` for detailed errors

### "Using rule-based scoring only"
- Groq API key not configured
- Get FREE key at https://console.groq.com/
- System still works but with simpler scoring

### "Telegram delivery failed"
- Verify bot token and chat ID
- Ensure bot is admin of channel (for channels)
- Test with: `python -c "from telegram_services.telegram_sender import TelegramSender; t = TelegramSender('TOKEN', 'ID'); print(t.test_connection())"`

### Translation errors
- Internet connection required for Google Translate
- Consider setting up proxy if in restricted region

## 📝 Updating TikTok Product Database

Weekly update recommended:

1. Export from TikTok Affiliate Center:
   - US: https://affiliate.tiktok.com/creator_center/product_explorer (US market)
   - UK: Switch to UK market and export

2. Save as CSV with columns: `title,price,category,market`

3. Replace files:
   - `data/tiktok_products_us.csv`
   - `data/tiktok_products_uk.csv`

## 🔒 Security Notes

- Never commit `.env` file (contains API keys)
- Keep Groq and TikHub keys secret
- Use environment variables in production
- Rotate API keys periodically

## 📄 License

MIT License - See LICENSE file

## 🤝 Support

For issues or questions:
1. Check `logs/scan.log` for error details
2. Review this README troubleshooting section
3. Verify all API keys are valid

---

**Built with ❤️ using Groq's free LLM tier**

Get your FREE Groq API key: https://console.groq.com/
