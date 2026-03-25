# 🚀 Quick Start Guide - Douyin Opportunity Finder

Get up and running in 5 minutes!

## Prerequisites

- Python 3.9+ installed
- Git (for cloning)
- Email account (Gmail recommended)

## Step 1: Clone & Install (2 minutes)

```bash
# Clone or navigate to the project
cd douyin_opportunity_finder

# Create virtual environment
python -m venv venv

# Activate it
# On Mac/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Get Your FREE API Keys (2 minutes)

### A. Groq API Key (Free LLM)

1. Go to https://console.groq.com/
2. Sign up (free, no credit card needed)
3. Click "API Keys" → "Create API Key"
4. Copy the key (starts with `gsk_...`)

### B. TikHub API Key

1. Go to https://tikhub.io/
2. Sign up for an account
3. Get your API key from dashboard

### C. Gmail App Password (for email reports)

1. Enable 2FA on your Google Account first
2. Go to https://myaccount.google.com/apppasswords
3. Select "Mail" → Your device
4. Copy the 16-character password

## Step 3: Configure Environment (1 minute)

```bash
# Copy the example config
cp .env.example .env

# Edit with your keys (use nano, vim, or notepad)
nano .env
```

Update these lines in `.env`:

```env
# Required - TikHub
TIKHUB_API_KEY=gsk_your_actual_key_here

# Required - Groq (FREE)
GROQ_API_KEY=gsk_your_actual_groq_key_here
GROQ_MODEL=llama-3.3-70b-versatile
LLM_PROVIDER=groq

# Required - Email (Gmail example)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=xxxx_xxxx_xxxx_xxxx  # 16-char app password
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=your_email@gmail.com,boss@company.com
ENABLE_EMAIL_REPORTS=true
```

## Step 4: Test Installation

```bash
# Run the test suite
python test_pipeline.py
```

Expected output:
```
✓ All imports successful
✓ Configuration loaded
✓ Data files found
✓ Agents initialized
✓ Pipeline ready
```

## Step 5: Run Your First Report

```bash
# Run the pipeline manually
python main.py
```

This will:
1. Fetch trending products from Douyin
2. Check against TikTok Shop databases
3. Score opportunities using Groq LLM
4. Generate markdown report (`data/daily_report.md`)
5. Generate PDF report (`data/daily_report.pdf`)
6. Email PDF to recipients (if configured)

## View Results

```bash
# View markdown report in terminal
cat data/daily_report.md

# Or open PDF (Mac)
open data/daily_report.pdf

# Or open PDF (Windows)
start data/daily_report.pdf

# Or open PDF (Linux)
xdg-open data/daily_report.pdf
```

## Schedule Daily Reports

### Option A: Python Scheduler (Easiest)

```bash
# Keep running in background
python scheduler.py &
```

### Option B: Cron Job (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 9 AM China time)
0 1 * * * TZ='Asia/Shanghai' cd /path/to/douyin_opportunity_finder && /path/to/venv/bin/python main.py
```

### Option C: Task Scheduler (Windows)

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at 1:00 AM
4. Action: Start a program
   - Program: `python.exe`
   - Arguments: `main.py`
   - Start in: `C:\path\to\douyin_opportunity_finder`

## Update TikTok Product Database (Weekly)

1. Export from TikTok Affiliate Center
2. Replace files in `data/` folder:
   - `tiktok_products_us.csv`
   - `tiktok_products_uk.csv`

## Troubleshooting

### "Groq API key not valid"
- Check you copied the entire key (starts with `gsk_`)
- Ensure no extra spaces in `.env`

### "Email failed to send"
- Use App Password, NOT your regular Gmail password
- Ensure 2FA is enabled on Google Account
- Check SMTP settings in `.env`

### "No gap products found"
- Make sure TikTok CSV files exist in `data/` folder
- Check CSV has column named `product_name`, `title`, or `name`

### "TikHub API error"
- Verify API key is correct
- Check API quota hasn't been exceeded
- System will use cached data if API fails

## Next Steps

✅ System is now running!  
✅ Check your email for PDF reports  
✅ Review `data/daily_report.md` for detailed analysis  
✅ Adjust scoring parameters in `config/config.yaml` if needed  

## Getting Help

1. Check logs: `cat logs/scan.log`
2. Review README.md for detailed documentation
3. Verify all API keys are correctly configured

---

**That's it! You're ready to find winning products! 🎉**

For detailed documentation, see [README.md](README.md) and [ARCHITECTURE.md](ARCHITECTURE.md).
