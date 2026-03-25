# System Architecture Overview

## How It All Works Together

The Douyin Opportunity Finder is a multi-agent pipeline that automates product research for TikTok Shop sellers. Here's a complete breakdown of how each component interacts.

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DAILY EXECUTION (9 AM CST)                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 1: DouyinScoutAgent                                               │
│  ─────────────────────                                                  │
│  • Calls TikHub API: /douyin/billboard/fetch_hot_rise_list             │
│  • Filters products by Chinese keywords (好物，推荐，爆款，etc.)          │
│  • Extracts: title, hot_count, item_id, url                            │
│  • Caches results to data/cache.json                                   │
│  • Output: JSON list of ~50 trending Douyin products                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 2: TikTokCheckerAgent                                             │
│  ───────────────────────                                                │
│  • Loads TikTok product databases (US & UK CSVs)                       │
│  • Translates Chinese titles → English (googletrans)                   │
│  • Fuzzy matches against TikTok products (SequenceMatcher)             │
│  • Threshold: ≥0.8 similarity = "already exists"                       │
│  • Output: List of "gap" products NOT on TikTok Shop                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 3: MarketValidatorAgent                                           │
│  ────────────────────────                                               │
│  For EACH gap product:                                                  │
│  • Search Amazon (competition, price, sellers)                         │
│  • Search Reddit (sentiment, mentions)                                 │
│  • Score 5 dimensions (0-2 points each):                               │
│    - Competition level                                                   │
│    - Reddit sentiment                                                   │
│    - Cultural fit                                                       │
│    - Visual appeal                                                      │
│    - Price point ($10-50 ideal)                                        │
│  • Total score: 0-10                                                    │
│  • Output: Validated products with scores                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 4: ReporterAgent                                                  │
│  ───────────────                                                        │
│  • Generates markdown table (top 20 opportunities)                     │
│  • Creates detailed analysis (top 10 products)                         │
│  • Adds content angle suggestions                                      │
│  • Saves to: data/daily_report.md                                      │
│  • Sends notification (Slack/Email/Telegram - configurable)            │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Configuration Layer (`config/`)

**File: `config/__init__.py`**
- Central configuration management
- Loads `.env` environment variables
- Parses `config.yaml` for agent settings
- Provides properties for all paths and settings

**Key Settings:**
```python
config.tikhub_api_key        # TikHub API authentication
config.fuzzy_match_threshold # 0.8 = 80% similarity threshold
config.schedule_hour         # 9 (AM China time)
config.timezone              # Asia/Shanghai
config.tiktok_products_us_csv # Path to US database
config.tiktok_products_uk_csv # Path to UK database
```

### 2. Agent Layer (`agents/`)

#### DouyinScoutAgent (`douyin_scout.py`)

**Purpose:** Fetch trending products from Douyin

**Methods:**
- `fetch_hot_rise_list()` - API call to TikHub
- `filter_product_titles()` - Filter by keywords
- `extract_product_info()` - Standardize data format
- `save_cache()` / `load_cache()` - Fallback mechanism

**Data Flow:**
```
TikHub API → Raw JSON → Filter → Extract → Cache → Output JSON
```

#### TikTokCheckerAgent (`tiktok_checker.py`)

**Purpose:** Identify products not on TikTok Shop

**Methods:**
- `load_tiktok_databases()` - Load US & UK CSVs
- `translate_title()` - Chinese → English translation
- `fuzzy_match()` - SequenceMatcher similarity
- `check_product_exists()` - Compare against database

**Algorithm:**
```python
for each douyin_product:
    english_title = translate(chinese_title)
    best_ratio = max(fuzzy_match(english_title, tiktok_product))
    if best_ratio < 0.8:
        add_to_gaps(douyin_product)
```

#### MarketValidatorAgent (`market_validator.py`)

**Purpose:** Score market potential

**Scoring Breakdown:**
```
Competition (0-2 pts):
  2.0 = No sellers on Amazon
  1.8 = <10 sellers
  1.5 = 10-50 sellers
  1.0 = 50-100 sellers
  0.5 = >100 sellers

Sentiment (0-2 pts):
  2.0 = Positive Reddit buzz
  1.5 = No mentions (untapped)
  0.5 = Negative sentiment

Cultural Fit (0-2 pts):
  +0.2 for each trend keyword (ASMR, LED, Apple, etc.)
  Max 2.0 points

Visual Appeal (0-2 pts):
  +0.3 for visual categories (light, transform, before/after)
  Max 2.0 points

Price Point (0-2 pts):
  2.0 = $10-50 (ideal)
  1.5 = $5-10 or $50-75
  1.0 = Outside range
```

#### ReporterAgent (`reporter.py`)

**Purpose:** Generate actionable report

**Output Sections:**
1. Executive Summary (metrics, totals)
2. Opportunity Table (top 20, markdown format)
3. Detailed Analysis (top 10, score breakdowns)
4. Action Items (prioritized tasks)

**Content Angle Generator:**
```python
if 'LED' in product_name:
    return "Show dramatic before/after lighting transformation"
elif 'organize' in product_name:
    return "Satisfying organization timelapse with ASMR"
else:
    return "Hook → Problem → Solution → CTA"
```

### 3. Pipeline Orchestration (`main.py`)

**OpportunityFinderPipeline Class:**

```python
class OpportunityFinderPipeline:
    def __init__(self, config):
        self.scout = DouyinScoutAgent(config)
        self.checker = TikTokCheckerAgent(config)
        self.validator = MarketValidatorAgent(config)
        self.reporter = ReporterAgent(config)
    
    async def run_pipeline(self):
        # Step 1: Fetch Douyin
        douyin_result = await self.scout.run()
        
        # Step 2: Check gaps
        checker_result = await self.checker.run(douyin_result)
        
        # Step 3: Validate
        validator_result = await self.validator.run(checker_result)
        
        # Step 4: Report
        report = await self.reporter.run(validator_result)
        
        return report
```

### 4. Scheduling Layer (`scheduler.py`)

**Options:**

**A. Python Scheduler (schedule library):**
```python
schedule.every().day.at("09:00").do(pipeline.run_pipeline())
```

**B. Cron Job:**
```bash
0 1 * * * TZ='Asia/Shanghai' cd /app && python main.py
```
(Run at 1 AM UTC = 9 AM China time)

**C. OpenClaw (when available):**
```bash
openclaw cron add "python main.py" --schedule="0 9 * * *"
```

### 5. Utilities (`utils.py`)

**Functions:**
- `setup_logging()` - Configure file + console logging
- `format_timestamp()` - ISO format timestamps
- `parse_chinese_number()` - Handle "万", "亿" units

## Data Flow Diagram

```
                    ┌─────────────────┐
                    │   TikHub API    │
                    │  (Douyin Data)  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  DouyinScout    │
                    │     Agent       │
                    └────────┬────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  JSON: Douyin Products       │
              │  [{title, hot_count, ...}]   │
              └──────────────┬───────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
    ┌─────────────────────┐   ┌─────────────────────┐
    │  TikTok US CSV      │   │  TikTok UK CSV      │
    │  (Weekly Export)    │   │  (Weekly Export)    │
    └──────────┬──────────┘   └──────────┬──────────┘
               │                         │
               └────────────┬────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ TikTokChecker   │
                   │     Agent       │
                   └────────┬────────┘
                            │
                            ▼
              ┌──────────────────────────────┐
              │  JSON: Gap Products          │
              │  (Not on TikTok Shop)        │
              └──────────────┬───────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
    ┌─────────────────────┐   ┌─────────────────────┐
    │  Amazon Search      │   │  Reddit Search      │
    │  (Competition)      │   │  (Sentiment)        │
    └──────────┬──────────┘   └──────────┬──────────┘
               │                         │
               └────────────┬────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │MarketValidator  │
                   │     Agent       │
                   └────────┬────────┘
                            │
                            ▼
              ┌──────────────────────────────┐
              │  JSON: Scored Products       │
              │  [{score: 8.5, ...}]         │
              └──────────────┬───────────────┘
                             │
                             ▼
                   ┌─────────────────┐
                   │  ReporterAgent  │
                   └────────┬────────┘
                            │
                            ▼
              ┌──────────────────────────────┐
              │  Markdown Report             │
              │  data/daily_report.md        │
              └──────────────────────────────┘
```

## Error Handling Strategy

### API Failures
```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential())
def fetch_hot_rise_list():
    # Retry with exponential backoff
```

### Fallback Chain
```
API Success → Use fresh data
     ↓ (fail)
Load Cache → Use yesterday's data
     ↓ (fail)
Return Error → Log and notify
```

### Logging
```python
logger.info("Step completed")      # Normal operation
logger.warning("Using cache")       # Recoverable issue
logger.error("API failed")          # Serious problem
logger.critical("Pipeline crash")   # System failure
```

## Extension Points

### Adding New Data Sources

1. **New API Source:**
   - Create new agent in `agents/`
   - Implement `async run()` method
   - Add to pipeline in `main.py`

2. **New Validation Source:**
   - Extend `MarketValidatorAgent`
   - Add scoring dimension
   - Update `score_product()` method

3. **New Output Format:**
   - Extend `ReporterAgent`
   - Add format method (PDF, HTML, etc.)
   - Update `generate_report()`

### Customizing Scoring

Edit `agents/market_validator.py`:

```python
def score_product(self, product, amazon_data, reddit_data):
    # Add custom scoring criteria
    scores['my_custom_metric'] = self._evaluate_custom(product)
```

### Adding Notifications

Edit `scheduler.py`:

```python
def send_notification(self, report):
    # Email
    smtp.send_email(report)
    
    # Slack
    requests.post(SLACK_WEBHOOK, json={'text': report})
    
    # Telegram
    telegram_bot.send_message(report)
```

## Performance Considerations

### Optimization Strategies

1. **Caching:**
   - API responses cached to `data/cache.json`
   - TikTok databases loaded once per run
   - Translation results could be cached

2. **Parallel Processing:**
   ```python
   # Future enhancement
   import asyncio
   await asyncio.gather(
       validate_product(p1),
       validate_product(p2),
       validate_product(p3)
   )
   ```

3. **Rate Limiting:**
   - TikHub API: Respect rate limits
   - Amazon/Reddit: Add delays between requests
   - Use tenacity for retry logic

### Memory Usage

- TikTok databases: ~1000 products = <1MB
- Product data: ~50 items = negligible
- Logs: Rotated daily (implement log rotation)

## Security Best Practices

### Environment Variables
```bash
# NEVER commit .env file
TIKHUB_API_KEY=secret_key_here
OPENAI_API_KEY=secret_key_here
```

### Git Ignore
```gitignore
.env
*.log
data/cache.json
data/daily_report.md
```

### API Key Handling
```python
# Load from environment only
api_key = os.getenv('TIKHUB_API_KEY')
if not api_key:
    raise ValueError("API key not configured")
```

## Monitoring & Maintenance

### Daily Checks
- Review `logs/scan.log` for errors
- Verify report generated in `data/daily_report.md`
- Check API quota usage

### Weekly Tasks
- Update TikTok CSV exports
- Review top-scoring products manually
- Adjust scoring weights if needed

### Monthly Reviews
- Analyze which predictions were accurate
- Refine scoring algorithm
- Update trend keywords

---

This architecture provides a robust, extensible foundation for automated product research. Each component is modular and can be enhanced independently while maintaining the overall pipeline flow.
