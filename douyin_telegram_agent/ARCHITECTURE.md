# System Architecture

## Overview

The Douyin Opportunity Finder is built on a multi-agent architecture using a pipeline pattern. Each agent has a single responsibility, making the system modular, testable, and maintainable.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SCHEDULER                                 │
│                   (Daily at 9 AM CST)                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MAIN PIPELINE                                │
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │   Scout      │ → │   Checker    │ → │  Validator   │        │
│  │   Agent      │   │   Agent      │   │   Agent      │        │
│  └──────────────┘   └──────────────┘   └──────────────┘        │
│         │                  │                  │                 │
│         ▼                  ▼                  ▼                 │
│  TikHub API          Translation        Groq LLM                │
│  (Douyin Data)       Fuzzy Match        (Scoring)               │
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │   Reporter   │ ← │    PDF       │ ← │  Telegram    │        │
│  │   Agent      │   │  Generator   │   │   Sender     │        │
│  └──────────────┘   └──────────────┘   └──────────────┘        │
│         │                  │                  │                 │
│         ▼                  ▼                  ▼                 │
│   Markdown           PDF Report         Telegram Bot            │
│   Report             (A4 Format)        (Message + File)        │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Configuration Layer (`config/`)

**Purpose**: Centralized configuration management

**Files**:
- `__init__.py` - Config loader class
- `config.yaml` - Agent parameters, paths, logging settings

**Responsibilities**:
- Load environment variables (.env)
- Parse YAML configuration
- Provide type-safe access to settings
- Manage file paths (absolute/relative)

**Key Classes**:
```python
class Config:
    - tikhub_api_key: str
    - groq_api_key: str
    - telegram_bot_token: str
    - telegram_chat_id: str
    - get_agent_config(name) -> dict
    - get_paths() -> dict
    - get_logging_config() -> dict
```

### 2. Agent Layer (`agents/`)

#### A. DouyinScoutAgent

**Purpose**: Fetch trending products from Douyin via TikHub API

**Flow**:
```
TikHub API → Parse Response → Filter Keywords → Cache → Return
```

**Key Methods**:
- `fetch_trending_products()` - Main API call with retry logic
- `_parse_response()` - Extract product data
- `_is_product_related()` - Filter by Chinese keywords
- `_cache_products()` - Local JSON cache for fallback

**Error Handling**:
- Exponential backoff retry (3 attempts)
- Falls back to cached data on API failure
- Logs all errors with timestamps

#### B. TikTokCheckerAgent

**Purpose**: Identify products NOT available on TikTok Shop US/UK

**Flow**:
```
Chinese Title → Translate → Fuzzy Match → Similarity Score → Gap Detection
```

**Key Methods**:
- `translate_title()` - Chinese to English (Google Translate)
- `calculate_similarity()` - SequenceMatcher fuzzy matching
- `check_product_exists()` - Compare against database
- `find_gaps()` - Filter products with similarity < 0.8

**Algorithm**:
```python
for each douyin_product:
    english_title = translate(chinese_title)
    max_sim = 0
    for each tiktok_product:
        sim = sequence_matcher(english, tiktok)
        if sim > max_sim: max_sim = sim
    if max_sim < 0.8: 
        add_to_gaps()
```

#### C. MarketValidatorAgent

**Purpose**: Score products 1-10 using AI analysis

**Flow**:
```
Product Name → Groq LLM → 5-Dimension Scoring → Weighted Average
```

**Scoring Dimensions**:
1. **Competition** (25% weight) - Amazon saturation
2. **Sentiment** (20% weight) - Reddit/social buzz
3. **Cultural Fit** (25% weight) - Western appeal
4. **Visual Appeal** (20% weight) - Video potential
5. **Price Point** (10% weight) - Ideal $10-50 range

**LLM Prompt Structure**:
```
You are an e-commerce analyst...
Analyze: "{product_name}"
Hot Count: {number}

Score 1-10 on:
- Competition
- Sentiment  
- Cultural Fit
- Visual Appeal
- Price Point

Output format:
COMPETITION: X
SENTIMENT: X
...
CONTENT_ANGLE: ...
NOTES: ...
```

**Fallback**: Rule-based scoring when Groq unavailable

#### D. ReporterAgent

**Purpose**: Generate markdown reports and summaries

**Output Structure**:
- Executive summary
- Top 20 opportunities table
- Detailed top 10 analysis
- Action items

### 3. Reporting Layer (`reporting/`)

#### PDFGenerator

**Purpose**: Create professional A4 PDF reports

**Technology**: ReportLab

**PDF Sections**:
1. Header (title, date, metrics)
2. Executive summary
3. Top 20 opportunities table (color-coded scores)
4. Detailed top 10 analysis
5. Action items & recommendations
6. Footer

**Styling**:
- Custom color scheme (#2c5282 primary)
- Alternating row colors in tables
- Emoji indicators (🟢🟡🔴)
- Professional fonts (Helvetica)

### 4. Delivery Layer (`telegram_services/`)

#### TelegramSender

**Purpose**: Deliver reports to Telegram

**API**: Telegram Bot API (https://api.telegram.org/bot{token}/...)

**Methods**:
- `send_document()` - Send PDF file
- `send_message()` - Send text summary
- `send_report()` - Combined message + PDF
- `test_connection()` - Verify bot setup

**Async Support**: Uses httpx for async HTTP requests

### 5. Orchestration Layer

#### main.py (Pipeline)

**Workflow**:
```python
1. Initialize all agents
2. scout.fetch_trending_products()
3. checker.find_gaps(products)
4. validator.validate_batch(gaps)
5. reporter.generate_markdown_report()
6. pdf_generator.generate_pdf()
7. telegram_sender.send_report()
8. Log results
```

**Error Handling**:
- Try-catch around entire pipeline
- Results dictionary tracks success/failure
- Comprehensive logging at each step

#### scheduler.py

**Purpose**: Run pipeline daily at 9 AM China time

**Implementation**: Python `schedule` library

**Options**:
- Keep running as background process
- Cron job (Linux/Mac)
- Windows Task Scheduler

### 6. Data Layer

**File Structure**:
```
data/
├── tiktok_products_us.csv    # US market database
├── tiktok_products_uk.csv    # UK market database
├── douyin_cache.json         # API response cache
├── daily_report_*.md         # Generated reports
└── daily_report_*.pdf        # Generated PDFs
```

**CSV Format**:
```csv
title,price,category,market
Wireless Earbuds,$29.99,Electronics,US
```

## Data Flow

```
User Input (.env)
     ↓
Configuration → Agents → Reports → Telegram
     ↓              ↓         ↓         ↓
  API Keys    TikHub     PDF      Bot Token
              Google     Gen      Chat ID
              Translate
              Groq
```

## Execution Timeline

Typical run (50 products):
```
00:00 - Pipeline start
00:02 - DouyinScout: Fetch products (2s)
00:05 - TikTokChecker: Translate & match (3s)
00:30 - MarketValidator: Score gaps (25s, LLM calls)
00:32 - Reporter: Generate markdown (2s)
00:35 - PDFGenerator: Create PDF (3s)
00:37 - TelegramSender: Upload & send (2s)
00:38 - Pipeline complete
```

Total: ~38 seconds for full pipeline

## Security Considerations

1. **API Keys**: Stored in .env (gitignored)
2. **No Hardcoded Secrets**: All keys from environment
3. **Rate Limiting**: Built-in retry with backoff
4. **Data Privacy**: No user data stored
5. **Logging**: Sanitized (no keys in logs)

## Extensibility

### Adding New Data Sources

1. Create new agent (e.g., `KuaishouScoutAgent`)
2. Implement standard interface:
   ```python
   def fetch_products() -> List[Dict]
   ```
3. Add to pipeline initialization

### Adding New Validation Criteria

1. Update `MarketValidatorAgent._analyze_with_llm()`
2. Modify prompt template
3. Adjust weights in `score_product()`

### Adding New Output Formats

1. Create generator class (e.g., `ExcelGenerator`)
2. Implement `generate(data, path)` method
3. Call in pipeline after PDF generation

## Performance Optimization

**Current Bottlenecks**:
1. LLM API calls (sequential)
2. Translation API calls (sequential)

**Future Improvements**:
- Batch LLM requests
- Parallel translation
- Redis caching for repeated products
- Database instead of CSV

## Monitoring & Debugging

**Logs Location**: `logs/scan.log`

**Log Levels**:
- INFO: Normal operation
- WARNING: Non-critical issues
- ERROR: Failures requiring attention

**Key Metrics Logged**:
- Products fetched
- Gaps identified
- Average scores
- Execution time
- Errors encountered

## Testing Strategy

**Unit Tests** (`test_pipeline.py`):
- Import verification
- Configuration loading
- Agent initialization
- Translation accuracy
- Report generation

**Integration Tests**:
- Full pipeline run (mocked APIs)
- End-to-end with test data

**Manual Testing**:
- Real API calls (weekly)
- Telegram delivery verification
- PDF quality check

---

This architecture provides a robust, scalable foundation for automated product opportunity discovery with clear separation of concerns and comprehensive error handling.
