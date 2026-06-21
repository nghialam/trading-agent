# System Architecture Specification

## Autonomous Trading Agent - Scalable 24/7 System

**Version:** 2.1.0  
**Date:** 2026-06-21  
**Author:** Nghia Lam  
**Changelog:** Fixed scanner stability, added signal deduplication, enhanced error handling

---

## 1. Overview

This document describes the system architecture of a scalable, 24/7 automated stock scanning and signal management system built for the Vietnamese stock market (HOSE, HNX, UPCOM).

The system consists of three core components:

1. **Backend Scanner Service** — Multi-threaded service that continuously monitors the watchlist and generates trading signals
2. **Centralized Database** — PostgreSQL with normalized schema for storing signals, price data, and configuration
3. **Web-based Management Dashboard** — Streamlit UI for monitoring signals, managing watchlist, and viewing analytics

```
┌─────────────────────────────────────────────────────────────┐
│                      24/7 Automated Trading System               │
├─────────────────────────────────────────────────────────────┤
│                                                                  │
│      ┌──────────────┐           ┌──────────────┐           ┌──────────┐ │
│      │ Scanner         │──────▶│ PostgreSQL       │──────▶│ Streamlit   │ │
│      │ Service         │        │ Database         │        │ Dashboard   │ │
│      │ (FastAPI)       │        │                 │        │             │ │
│      └──────────────┘        └──────────────┘        └──────────┘ │
│            │                            │                          │     │
│            ▼                             ▼                           │     │
│   vnstock API              Signal Storage                               │     │
│   Market Data              Watchlist Config                              │     │
└───────────────────────────────────────────────────────────────┘       │
```

## 2. High-Level Architecture

### 2.1 Component Diagram

```
                     ┌─────────────────────┐
                     │   TradingAgent        │
                     │    (Orchestrator)     │
                     └──────────┬──────────┘
                                │
               ┌────────────────┼────────────────┐
               │                 │                 │
      ┌───────────┐       ┌───────────┐       ┌───────────┐
      │ Data        │       │ Evaluation│       │ Signal     │
      │ Scanner     │       │ Engine     │       │ Generator │
      └───────────┘       └───────────┘       └───────────┘
                                 │
                         ┌───────────┐
                         │ Dispatcher│
                         └───────────┘
                                │
                     ┌───────────┐
                     │ Scanner    │
                     │ Service    │
                     └───────────┘
                                │
                     ┌───────────┐
                     │ PostgreSQL │
                     └───────────┘
```

### 2.2 Data Flow

1. **Input**: Raw OHLCV (Open, High, Low, Close, Volume) data from market source
2. **Scan**: Validate and clean incoming data
3. **Evaluate**: Compute technical indicators (RSI, MACD, Bollinger Bands, etc.)
4. **Generate**: Apply strategy logic to produce trading signals (BUY/SELL/HOLD)
5. **Dispatch**: Execute trades via broker API or webhook
6. **Store**: Persist signals and metadata to PostgreSQL database
7. **Monitor**: Display real-time data via Streamlit dashboard

### 2.3 Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Data Source | vnstock | Vietnamese stock market data access |
| Technical Analysis | pandas-ta / custom | RSI, MACD, Bollinger Bands, ATR, EMA, SMA |
| Backend API | FastAPI >= 0.100 | RESTful API for frontend and external integrations |
| Web Dashboard | Streamlit >= 1.28 | Real-time signal monitoring and management |
| Database | PostgreSQL >= 14 | Persistent storage with normalized schema |
| ORM | SQLAlchemy >= 2.0 | Object-relational mapping |
| Data Processing | pandas >= 2.0 | DataFrame operations |
| Numerical Computing | numpy >= 1.24 | Array computations |
| HTTP Client | requests >= 2.31 | API communication |
| Configuration | pyyaml >= 6.0 | YAML config parsing |
| Backtesting | backtrader >= 1.97 | Historical strategy testing |

## 3. Component Details

### Component 1: Scanner Service (`services/scanner.py`)

**Responsibility**: Multi-threaded stock market scanner that continuously monitors the watchlist and generates trading signals.

**Class**: `ScannerService`

**Key Features**:
- ThreadPoolExecutor for parallel scanning of watchlist stocks
- Priority-based update frequency (VN30 stocks scanned more frequently)
- Automated error recovery with retry logic
- Real-time configuration reload from database
- Comprehensive logging for all scanner activities

**Methods**:
| Method | Description |
|--------|-------------|
| `scan_stock(stock)` | Scan a single stock and generate signals |
| `_fetch_historical_data(symbol, days)` | Fetch OHLCV data from vnstock API |
| `_evaluate_signals(rsi, macd, macd_signal, price)` | Evaluate indicators to generate signal |
| `_save_signal(...)` | Save generated signal to database |
| `run()` | Main scanner loop (runs continuously) |
| `stop()` | Graceful shutdown |

**Scanner Parameters**:
```yaml
scanner:
    scan_interval: 30             # Default scan interval (seconds)
    high_priority_interval: 10    # VN30 stocks
    low_priority_interval: 60     # Other stocks
    max_workers: 10               # Thread pool size
```

### Component 2: Database Layer (`database/`)

**Purpose**: PostgreSQL database with normalized schema for storing signals, price data, and configuration.

#### Tables

##### `Watchlist`
Active stocks to monitor.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PK | Primary key |
| symbol | VARCHAR(10) UNIQUE | Stock ticker symbol |
| name | TEXT | Company name |
| sector | VARCHAR(50) | Industry sector |
| priority | INTEGER (1-3) | 1=high (VN30), 2=medium, 3=low |
| enabled | BOOLEAN | Whether stock is active |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

##### `Signal`
Generated trading signals with full metadata.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PK | Primary key |
| symbol | VARCHAR(10) | Stock ticker symbol |
| timestamp | TIMESTAMP | Signal generation time |
| signal_type | VARCHAR(10) | BUY / SELL / HOLD |
| confidence_score | FLOAT | Signal confidence (0.0 - 1.0) |
| price_at_signal | FLOAT | Stock price at signal time |
| indicators | JSON | Technical indicator values |
| metadata | JSON | Additional context |
| processed | BOOLEAN | Whether signal was acted upon |
| created_at | TIMESTAMP | Creation timestamp |

##### `PriceData`
Historical OHLCV data.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PK | Primary key |
| symbol | VARCHAR(10) | Stock ticker symbol |
| timestamp | TIMESTAMP | Data point time |
| open | FLOAT | Opening price |
| high | FLOAT | Highest price |
| low | FLOAT | Lowest price |
| close | FLOAT | Closing price |
| volume | BIGINT | Trading volume |

##### `SystemLog`
Activity logging for all scanner operations.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PK | Primary key |
| timestamp | TIMESTAMP | Log entry time |
| level | VARCHAR(10) | INFO / WARNING / ERROR / DEBUG |
| component | VARCHAR(50) | Component name |
| message | TEXT | Log message |
| details | JSON | Additional context |

##### `ScannerConfig`
Runtime configuration key-value store.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PK | Primary key |
| key | VARCHAR(50) UNIQUE | Configuration key |
| value | TEXT | Configuration value |
| updated_at | TIMESTAMP | Last update timestamp |

#### Indexes

| Index Name | Table | Columns | Purpose |
|-----------|-------|---------|---------|
| `idx_signal_symbol_time` | Signal | (symbol, timestamp) | Query signals by stock and date range |
| `idx_signal_confidence` | Signal | (confidence_score) | Filter by signal strength |
| `idx_signal_type` | Signal | (signal_type) | Filter by signal type |
| `idx_price_data_symbol_time` | PriceData | (symbol, timestamp) | Query historical data |
| `idx_systemlog_level` | SystemLog | (level) | Filter by log level |

### Component 3: FastAPI Backend (`api/`)

**Purpose**: RESTful API for signal CRUD operations, watchlist management, and scanner control.

**Endpoints**:

#### Signals
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/signals` | List all signals (with filters: symbol, date_range, type) |
| GET | `/api/signals/{id}` | Get signal details by ID |
| POST | `/api/signals` | Create new signal (manual trigger) |
| DELETE | `/api/signals/{id}` | Delete signal by ID |

#### Watchlist
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/watchlist` | List all watchlist stocks |
| POST | `/api/watchlist` | Add stock to watchlist |
| PUT | `/api/watchlist/{id}` | Update stock configuration |
| DELETE | `/api/watchlist/{id}` | Remove from watchlist |

#### Scanner
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/scanner/status` | Get scanner running status |
| POST | `/api/scanner/start` | Start scanning service |
| POST | `/api/scanner/stop` | Stop scanning service |
| POST | `/api/scanner/restart` | Restart scanner with fresh executor |
| POST | `/api/scanner/scan/{symbol}` | Manually scan single stock |
| GET | `/api/scanner/config` | Get scanner configuration |
| PUT | `/api/scanner/config` | Update scanner configuration |
| GET | `/api/scanner/logs` | Get scanner activity logs |

### DailySummary Table

Stores daily price summaries for each stock.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PK | Primary key |
| date | TIMESTAMP | Date of summary (midnight) |
| symbol | VARCHAR(20) | Stock ticker |
| summary_text | TEXT | Human-readable summary |
| notable_events | JSON | Array of notable events |
| trading_notes | TEXT | Trading recommendations |
| market_conditions | JSON | Market trend analysis |
| volume_analysis | JSON | Volume statistics |

**Unique Constraint**: `(date, symbol)` - One summary per stock per day.

### Signal Reviews Table

Stores curated reviews for position changes (BUY/SELL transitions).

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PK | Primary key |
| signal_id | INTEGER FK | Reference to Signal |
| symbol | VARCHAR(20) | Stock ticker |
| previous_signal | VARCHAR(10) | Previous signal type |
| current_signal | VARCHAR(10) | New signal type |
| is_position_change | BOOLEAN | Always true for reviews |
| llm_analysis | JSON | Full LLM analysis |
| llm_verdict | VARCHAR(20) | QUALIFIED/WEAK/FAKE |
| llm_confidence | FLOAT | LLM confidence score |
| analysis_notes | TEXT | Human-readable notes |

### Pocket Pivot Data Table

Stores Pocket Pivot indicator calculations from 1H timeframe data.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PK | Primary key |
| symbol | VARCHAR(20) | Stock ticker |
| timestamp | TIMESTAMP | Calculation time |
| pivot_type | VARCHAR(20) | NONE/BULLISH/BEARISH |
| pivot_price | FLOAT | Price at pivot |
| volume_ratio | FLOAT | Volume ratio vs average |
| is_valid | BOOLEAN | Whether pivot is valid |
| previous_high | FLOAT | Previous period high |
| previous_low | FLOAT | Previous period low |
| context_data | JSON | Additional context |

### Scanner Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `scan_interval` | 30s | Default scan interval between cycles |
| `high_priority_interval` | 10s | Scan interval for VN30 stocks (deprecated) |
| `low_priority_interval` | 60s | Scan interval for other stocks (deprecated) |
| `max_workers` | 10 | Thread pool size for parallel scanning |
| `api_retry_attempts` | 3 | Retry attempts for vnstock API calls |
| `api_retry_delay` | 5s | Base delay for API retries (exponential backoff) |
| `dedup_window` | 5min | Signal deduplication window |

### Error Handling Strategy

The scanner implements robust error handling at multiple levels:

1. **API Level**: vnstock API calls retry 3 times with exponential backoff (5s, 10s, 20s)
2. **Thread Level**: Individual scan failures are caught and logged, next cycle retries
3. **Database Level**: Transaction rollbacks on constraint violations, graceful degradation
4. **Executor Level**: Automatic executor recreation if `RuntimeError` occurs
5. **Loop Level**: Scanner loop continues on any exception, sleeps 10s before retry

```python
# Example: Thread-safe scan execution
for stock in self.watchlist:
    try:
        future = executor.submit(self.scan_stock, stock)
        futures.append(future)
    except RuntimeError:
        # Recreate executor and retry
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
```

## 4. Pipeline Stages

### Stage 1: Market Scanning (`src/scanning.py`)

**Responsibility**: Ingest and validate raw market data  
**Class**: `DataScanner`  
**Input**: Raw OHLCV DataFrame  
**Output**: Validated OHLCV DataFrame  

**Validation Rules**:
- Data must not be empty
- Required columns: `open`, `high`, `low`, `close`, `volume`
- Cache last valid data for fallback

### Stage 2: Evaluation (`src/evaluation.py`)

**Responsibility**: Compute technical indicators  
**Class**: `EvaluationEngine`  
**Input**: Validated OHLCV DataFrame  
**Output**: DataFrame with added indicator columns  

**Computed Indicators**:
| Indicator | Parameters | Purpose |
|-----------|-----------|---------|
| RSI | 14 period | Momentum oscillator |
| MACD | 12, 26, 9 | Trend following |
| Bollinger Bands | 20 period, 2 std | Volatility bands |
| EMA | 12, 26 periods | Exponential moving average |
| ATR | 14 period | Volatility measure |
| SMA | 20, 50 periods | Simple moving average |

**Fallback**: If `pandas-ta` is not installed, uses custom numpy-based implementations.

### Stage 3: Signal Generation (`src/strategy.py`)

**Responsibility**: Evaluate indicators and generate trading signals  
**Class**: `SignalGenerator`  
**Input**: DataFrame with technical indicators  
**Output**: `TradeSignal` object (BUY, SELL, or HOLD)  

**Strategies**:
- **RSI + MACD Strategy** (default): Combines RSI momentum with MACD crossover signals

**Features**:
- Cooldown mechanism (configurable, default 60 seconds)
- Confidence scoring
- Multiple strategy voting mechanism

### Stage 4: Signal Dispatch (`src/dispatcher.py`)

**Responsibility**: Execute trading signals via configured interfaces  
**Class**: `SignalDispatcher`  
**Input**: `TradeSignal` object  
**Output**: `DispatchResult` object  

**Execution Interfaces**:
1. **Broker API** (HTTP POST)
   - Supports Bearer token authentication
   - Configurable timeout and retries
   
2. **Webhook** (HTTP POST)
   - Alternative execution channel

**Resilience Features**:
- Circuit breaker pattern (configurable threshold, default 5 failures)
- Automatic retry with delay (default 3 retries, 1.0s delay)
- Failure tracking and circuit state management

## 5. Configuration System

### 5.1 Configuration File (`config/strategies.yaml`)

```yaml
strategies:
    - name: rsi_macd
      enabled: true
      parameters:
        rsi_period: 14
        rsi_overbought: 70
        rsi_oversold: 30
        macd_fast: 12
        macd_slow: 26
        macd_signal: 9

execution:
    execution_url: "https://api.broker.com/v1/orders"
    api_key: ""               # Set your API key
    secret_key: ""            # Set your secret key
    max_retries: 3
    retry_delay: 1.0
    timeout: 10
    circuit_breaker_threshold: 5

scanner:
    scan_interval: 30             # Default scan interval (seconds)
    high_priority_interval: 10    # VN30 stocks
    low_priority_interval: 60     # Other stocks
    max_workers: 10               # Thread pool size

general:
    symbol: "VNM"                 # Default symbol
    log_level: "INFO"
    cooldown_seconds: 60          # Cooldown between signals
    min_confidence: 0.5           # Minimum confidence to act
```

### 5.2 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/trading_agent` |
| `VNSTOCK_API_KEY` | vnstock API key | (empty) |
| `LOG_LEVEL` | Logging level | `INFO` |

## 6. Deployment Architecture

### 6.1 Local Development

```bash
# Terminal 1: Start PostgreSQL
brew services start postgresql

# Terminal 2: Initialize database
python -c "from database.config import init_db; init_db()"

# Terminal 3: Run scanner service
python -c "from services.scanner import get_scanner; get_scanner().run()"

# Terminal 4: Start FastAPI backend
uvicorn api.main:app --reload --port 8200

# Terminal 5: Launch Streamlit dashboard
streamlit run dashboard/app.py --server.port 8501
```

### 6.2 Production Deployment (Docker)

```bash
# Build and run all services
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 6.3 Systemd Service (Linux)

```ini
# /etc/systemd/system/trading-scanner.service
[Unit]
Description=Trading Agent Scanner Service
After=network.target postgresql.service

[Service]
Type=simple
User=trading
WorkingDirectory=/opt/trading-agent
ExecStart=/opt/trading-agent/venv/bin/python -c "from services.scanner import get_scanner; get_scanner().run()"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 7. Error Handling & Recovery

### Scanner Service
- **Connection Errors**: Automatic retry with exponential backoff
- **Calculation Failures**: Logged to SystemLog table, scanner continues
- **Missed Ticks**: Detected and logged, no data loss for historical queries
- **Graceful Shutdown**: ThreadPoolExecutor waits for running tasks to complete

### Database
- **Connection Pooling**: SQLAlchemy engine with pool_size=10, max_overflow=20
- **Automatic Reconnection**: Connection errors trigger reconnection attempts
- **Transaction Safety**: All database operations use transactions with rollback on failure

### API Layer
- **Request Validation**: Pydantic models validate all input
- **Circuit Breaker**: Prevents cascading failures to broker APIs
- **Health Checks**: `/api/health` endpoint for monitoring service status

## 8. Logging Strategy

All scanner activities are logged to both console and the `SystemLog` table:

| Log Level | When to Use | Examples |
|-----------|-------------|---------|
| INFO | Normal operations | Signal generated, stock scanned |
| WARNING | Recoverable issues | Slow API response, retry attempt |
| ERROR | Failed operations | Connection error, calculation failure |
| DEBUG | Detailed diagnostics | Data fetch details, indicator values |

**Logged Events**:
- Connection errors (vnstock API failures)
- Calculation failures (indicator computation errors)
- Missed ticks (scanning interval exceeded)
- Signal generation events (BUY/SELL/HOLD)
- Database operations (save, query, update)
- Configuration changes (reload, update)

---

**Version:** 2.1.0  
**Last Updated:** 2026-06-21
