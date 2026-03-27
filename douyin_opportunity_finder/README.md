# 🚀 Douyin Opportunity Finder

An automated system that finds trending products on Douyin (Chinese TikTok) that are not yet available on TikTok Shop in the US/UK markets, validates their market potential, and generates daily PDF reports sent via email.

## Overview

This system uses a multi-agent architecture powered by AG2 (AutoGen) to:

1. **Fetch** top-selling products from Douyin using the TikHub API
2. **Cross-reference** against TikTok Shop product databases (US & UK)
3. **Identify** products not yet available on TikTok Shop
4. **Validate** market fit using Amazon and Reddit data with **Groq free LLM**
5. **Score** each opportunity (1-10) based on competition, cultural fit, and visual potential
6. **Generate** daily markdown AND PDF reports with actionable insights
7. **Email** PDF reports to multiple recipients automatically
8. **Automate** execution at 9 AM China time using scheduler/cron

## Key Features

✅ **Free LLM Integration** - Uses Groq API (free tier) for intelligent product scoring  
✅ **PDF Reports** - Professional formatted reports with charts and tables  
✅ **Email Delivery** - Send reports to multiple recipients via SMTP  
✅ **Multi-Agent System** - AG2-powered agent collaboration  
✅ **Market Validation** - Amazon competition + Reddit sentiment analysis  
✅ **Smart Scoring** - 5-dimensional scoring (competition, sentiment, cultural fit, visual appeal, price)  

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐     ┌─────────────────┐
│  DouyinScout    │────▶│  TikTokChecker   │────▶│  MarketValidator  │────▶│   Reporter      │
│  Agent          │     │  Agent           │     │  Agent (Groq)     │     │   Agent         │
└─────────────────┘     └──────────────────┘     └───────────────────┘     └─────────────────┘
       │                       │                        │                         │
       ▼                       ▼                        ▼                         ▼
  TikHub API           TikTok CSV Databases      Groq LLM +               Markdown Report
  (Douyin Trends)      (US & UK Products)        Amazon/Reddit            + PDF + Email
```

## Project Structure

```
douyin_opportunity_finder/
├── main.py                 # Main pipeline orchestrator
├── scheduler.py            # Scheduling module (cron/OpenClaw)
├── utils.py                # Utility functions
├── config/
│   ├── __init__.py         # Configuration loader
│   └── config.yaml         # Agent and LLM configuration
├── agents/
│   ├── __init__.py
│   ├── douyin_scout.py     # Fetches Douyin trends
│   ├── tiktok_checker.py   # Checks TikTok Shop gaps
│   ├── market_validator.py # Validates market potential
│   └── reporter.py         # Generates reports
├── data/
│   ├── tiktok_products_us.csv   # US TikTok products (update weekly)
│   ├── tiktok_products_uk.csv   # UK TikTok products (update weekly)
│   └── cache.json               # API response cache
├── logs/
│   └── scan.log                 # Execution logs
├── .env.example                  # Environment variables template
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Prerequisites

- Python 3.9 or higher
- TikHub API key ([Get one here](https://tikhub.io/))
- **Groq API key** (FREE - [Get one here](https://console.groq.com/))
- Optional: OpenClaw account for advanced scheduling
- Optional: SMTP credentials for email delivery

## Installation

### Step 1: Clone and Setup

```bash
cd douyin_opportunity_finder

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API keys
nano .env  # Or use your preferred editor
```

Required configurations in `.env`:

```env
# TikHub API (required for Douyin data)
TIKHUB_API_KEY=your_tikhub_api_key_here

# Groq LLM (FREE - get key at https://console.groq.com/)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
LLM_PROVIDER=groq

# Email Configuration (for PDF report delivery)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password_here
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient1@example.com,recipient2@example.com
EMAIL_SUBJECT=Douyin Opportunity Finder - Daily Report
ENABLE_EMAIL_REPORTS=true

# Optional: OpenAI (fallback if not using Groq)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o

# Optional: OpenClaw for scheduling
OPENCLAW_ENABLED=false
OPENCLAW_API_KEY=your_openclaw_api_key_here
```

#### Getting a Free Groq API Key

1. Visit [https://console.groq.com/](https://console.groq.com/)
2. Sign up for a free account
3. Go to API Keys section
4. Create a new API key
5. Copy the key to your `.env` file

**Free Tier Limits:**
- ~30 requests/minute (varies by model)
- Multiple models available (Llama 3, Mixtral, etc.)
- No credit card required

#### Setting Up Gmail for Email Reports

1. Enable 2FA on your Google Account
2. Generate an App Password:
   - Go to: https://myaccount.google.com/apppasswords
   - Select "Mail" and your device
   - Copy the 16-character password
3. Use this password in `SMTP_PASSWORD` (not your regular password)

For other email providers:
- **Outlook**: `smtp-mail.outlook.com`, port 587
- **Yahoo**: `smtp.mail.yahoo.com`, port 587
- **Custom SMTP**: Check your provider's documentation

### Step 3: Prepare TikTok Product Databases

Download your TikTok Shop product exports:

1. Go to [TikTok Affiliate Center](https://affiliate.tiktok.com/)
2. Export product lists for US and UK markets
3. Save as CSV files in the `data/` directory:
   - `data/tiktok_products_us.csv`
   - `data/tiktok_products_uk.csv`

Expected CSV format:
```csv
product_name,price,rating,seller_count,category
Product Name,29.99,4.5,100,Category
```

The system will automatically detect columns named: `product_name`, `title`, or `name`.

## Usage

### Manual Execution

Run the pipeline once:

```bash
python main.py
```

Output:
- Console logs showing progress
- Report saved to `data/daily_report.md`
- Logs saved to `logs/scan.log`

### Scheduled Execution

#### Option A: Python Scheduler

```bash
python scheduler.py
```

This runs continuously and executes the pipeline daily at 9 AM China time.

#### Option B: Cron Job (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 9 AM China time)
0 1 * * * TZ='Asia/Shanghai' cd /path/to/douyin_opportunity_finder && /path/to/venv/bin/python main.py >> logs/scan.log 2>&1
```

Note: Adjust timezone offset based on your server location.

#### Option C: OpenClaw Scheduling

If you have OpenClaw configured:

```bash
# Using OpenClaw CLI
openclaw cron add "python /path/to/main.py" --schedule="0 9 * * *" --timezone="Asia/Shanghai"
```

### Viewing Reports

After execution, view the generated report:

```bash
cat data/daily_report.md
```

Or open in any markdown viewer.

## Agent Workflow

### 1. DouyinScoutAgent

- Calls TikHub API endpoint `/douyin/billboard/fetch_hot_rise_list`
- Filters products by keywords: 好物，推荐，爆款，热销，etc.
- Extracts: title, hot_count, item_id, url
- Caches results for fallback

### 2. TikTokCheckerAgent

- Loads TikTok product CSVs (US & UK)
- Translates Chinese titles to English using **deep-translator**
- Performs fuzzy matching (SequenceMatcher) with threshold 0.8
- Returns list of "gap" products (not found on TikTok Shop)

### 3. MarketValidatorAgent

For each gap product:

- Searches Amazon for competition data (sellers, price, rating)
- Searches Reddit for sentiment analysis
- Scores 1-10 based on:
  - Competition level (0-2 points)
  - Reddit sentiment (0-2 points)
  - Cultural fit (0-2 points)
  - Visual appeal (0-2 points)
  - Price point $10-50 (0-2 points)

### 4. ReporterAgent

- Generates markdown table with top 20 opportunities
- Creates detailed analysis of top 10 products
- Includes content angle suggestions for TikTok videos
- Saves report to `data/daily_report.md`

## Scoring System

| Component | Criteria | Points |
|-----------|----------|--------|
| Competition | Fewer Amazon sellers = higher score | 0-2 |
| Sentiment | Positive Reddit mentions | 0-2 |
| Cultural Fit | Western market alignment (trends, keywords) | 0-2 |
| Visual Appeal | Can be demonstrated in 15-30s video | 0-2 |
| Price Point | Ideal range $10-50 | 0-2 |
| **Total** | | **0-10** |

## Customization

### Adjust Fuzzy Match Threshold

Edit `.env`:
```env
FUZZY_MATCH_THRESHOLD=0.8  # Lower = more lenient matching
```

### Change Schedule Time

Edit `.env`:
```env
SCHEDULE_HOUR=9
SCHEDULE_MINUTE=0
TIMEZONE=Asia/Shanghai
```

### Modify Scoring Weights

Edit `agents/market_validator.py` and adjust the scoring logic in `score_product()`.

### Add Notification Channels

Edit `scheduler.py` and implement `send_notification()` with your preferred method:
- Email (SMTP)
- Slack webhook
- Telegram bot
- Discord webhook

## Troubleshooting

### TikHub API Errors

- Check API key is correct in `.env`
- Verify API quota hasn't been exceeded
- System will fallback to cached data if API fails

### Translation Failures

- deep-translator may be rate-limited
- System falls back to keyword removal if translation fails
- Consider using DeepL API for production

### No Gap Products Found

- Ensure TikTok CSV files exist in `data/` directory
- Check CSV column names match expected format
- Lower `FUZZY_MATCH_THRESHOLD` in `.env`

### AG2 Import Errors

- AG2 integration is optional
- System falls back to sequential execution if AG2 not installed
- Install with: `pip install autogen-agentchat`

## Production Deployment

### Cloud Server Setup

Recommended: Tencent Cloud Lighthouse or similar VPS

1. Deploy code to server
2. Set up Python virtual environment
3. Configure systemd service for scheduler:

```ini
# /etc/systemd/system/douyin-finder.service
[Unit]
Description=Douyin Opportunity Finder
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/douyin_opportunity_finder
Environment="PATH=/home/ubuntu/douyin_opportunity_finder/venv/bin"
ExecStart=/home/ubuntu/douyin_opportunity_finder/venv/bin/python scheduler.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable douyin-finder
sudo systemctl start douyin-finder
```

### Weekly TikTok CSV Updates

Set a reminder to update TikTok product databases weekly:

```bash
# Add to crontab - runs every Monday at 8 AM
0 8 * * 1 echo "Remember to update TikTok CSV files!" | mail -s "Weekly Reminder" your@email.com
```

## API Integration Roadmap

### Current Status

| Integration | Status | Notes |
|-------------|--------|-------|
| TikHub API | ✅ Implemented | Requires API key |
| Deep Translator | ✅ Implemented | Free, reliable |
| Groq LLM | ✅ Implemented | FREE - llama-3.3-70b |
| PDF Generation | ✅ Implemented | Professional reports |
| Email Delivery | ✅ Implemented | SMTP-based |
| Amazon Search | ⚠️ Placeholder | Implement OpenClaw skill or API |
| Reddit Search | ⚠️ Placeholder | Implement PRAW or OpenClaw skill |
| OpenClaw Skills | ⚠️ Planned | amazon-search, reddit-readonly |
| AG2 Multi-Agent | ⚠️ Partial | Falls back to sequential |

### Future Enhancements

1. **OpenClaw Integration**: Implement actual amazon-search and reddit-readonly skills
2. **LLM Scoring**: Use GPT-4o for more nuanced market analysis
3. **Image Analysis**: Analyze product images for visual appeal scoring
4. **Price Tracking**: Monitor Amazon prices over time
5. **Competitor Alerts**: Notify when gap products appear on TikTok Shop

## License

MIT License - See LICENSE file for details.

## Support

For issues or questions:
1. Check logs in `logs/scan.log`
2. Review error messages in console output
3. Verify all API keys are correctly configured
4. Ensure TikTok CSV files are properly formatted

---

*Generated by Douyin Opportunity Finder v1.0*
