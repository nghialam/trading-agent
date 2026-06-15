# Module Specifications

## Autonomous Trading Agent - Scalable 24/7 System

**Version:** 2.0.0  
**Date:** 2026-06-15  

---

## Table of Contents

### Core Modules
1. [Module: src.agent](#1-module-srcagent)
2. [Module: src.scanning](#2-module-srcscanning)
3. [Module: src.evaluation](#3-module-srcevaluation)
4. [Module: src.strategy](#4-module-srcstrategy)
5. [Module: src.dispatcher](#5-module-srcdispatcher)
6. [Module: src.utils](#6-module-srcutils)
7. [Module: backtest](#7-module-backtest)

### New Modules (v2.0)
8. [Module: database.config](#8-module-databaseconfig)
9. [Module: database.models](#9-module-databasemodels)
10. [Module: services.scanner](#10-module-servicescanner)
11. [Module: api (FastAPI)](#11-module-api-fastapi)
12. [Module: dashboard (Streamlit)](#12-module-dashboard-streamlit)

---

## 1. Module: `src.agent`

### Purpose
Main trading agent class that orchestrates all pipeline stages in a coordinated workflow.

### Dependencies
- `src.scanning.DataScanner`
- `src.evaluation.EvaluationEngine`
- `src.strategy.SignalGenerator`, `TradeSignal`
- `src.dispatcher.SignalDispatcher`
- `src.utils.load_config`

### Class: `TradingAgent`

#### Responsibilities
1. Initialize all pipeline components (scanner, evaluator, generator, dispatcher)
2. Load and manage strategy configuration
3. Execute the four-stage pipeline for each data bar
4. Track trading state and signal history
5. Handle pipeline errors gracefully

#### State Management
| Attribute | Type | Purpose |
|-----------|------|---------|
| `symbol` | `str` | Trading symbol identifier |
| `scanner` | `DataScanner` | Data validation component |
| `evaluator` | `EvaluationEngine` | Technical analysis component |
| `generator` | `SignalGenerator` | Signal generation component |
| `dispatcher` | `SignalDispatcher` | Execution component |
| `is_running` | `bool` | Live trading state flag |
| `signals_received` | `list` | Signal history with dispatch results |
| `trades_executed` | `list` | Trade execution history |

#### Pipeline Execution Flow
```
run_pipeline(bar_data)
     │
     ├─► scanner.scan(bar_data)            # Validate data
     │
     ├─► evaluator.evaluate(scanned_data)   # Compute indicators
     │
     ├─► generator.generate_signal(evaluated_data)   # Generate signal
     │        │
     │        ├─► If BUY/SELL:
     │        │        └─► dispatcher.dispatch(signal)      # Execute trade
     │        │
     │        └─► Track signal in signals_received
     │
     └─► Return signal (or None for HOLD)
```

#### Error Handling
- All pipeline errors are caught at the top level
- Exceptions are logged with `exc_info=True` for debugging
- Returns `None` on failure (equivalent to HOLD)
- Does not propagate exceptions to caller

### Design Patterns Used
- **Orchestrator Pattern**: Coordinates multiple subsystems
- **Pipeline Pattern**: Sequential data processing stages
- **State Management**: Tracks trading state and history

---

## 2. Module: `src.scanning`

### Purpose
Market data scanning layer responsible for ingesting and validating market data before it enters the pipeline.

### Dependencies
- `pandas` (for DataFrame operations)

### Class: `DataScanner`

#### Responsibilities
1. Validate incoming OHLCV data structure
2. Check for required columns
3. Detect empty or malformed data
4. Cache last valid data for fallback scenarios

#### Validation Rules
| Rule | Condition | Action |
|------|-----------|--------|
| Not Empty | DataFrame must have rows | Raise `ValueError` if empty |
| Required Columns | Must contain: open, high, low, close, volume | Raise `ValueError` listing missing columns |

#### Data Flow
```
Input:  Raw OHLCV DataFrame (may be incomplete)
     │
     ├─► Check empty
     ├─► Check required columns
     └─► Return validated DataFrame
     │
Output: Validated OHLCV DataFrame
```

#### Caching Strategy
- `data_cache` stores last successfully scanned DataFrame
- Can be used as fallback in production scenarios
- Cache is updated on each successful scan

### Error Handling
- Raises `ValueError` for invalid data (fail-fast approach)
- Missing columns are reported explicitly for debugging
- Empty data detection prevents downstream processing errors

### Extension Points
- Add additional validation rules (e.g., price range checks)
- Implement data cleaning/transformation
- Add real-time streaming support

---

## 3. Module: `src.evaluation`

### Purpose
Evaluation engine that computes technical indicators from raw market data using pandas-ta or custom implementations.

### Dependencies
- `pandas` (DataFrame operations)
- `numpy` (numerical computations)
- `pandas_ta` (technical analysis functions) - optional, with fallback

### Class: `EvaluationEngine`

#### Responsibilities
1. Compute technical indicators on OHLCV data
2. Manage indicator cache
3. Provide fallback implementations when pandas_ta unavailable
4. Return enriched DataFrame with all indicators

#### Indicator Computation Pipeline
```
Input:  OHLCV DataFrame
     │
     ├─► Try pandas_ta (preferred)
     │    ├─► RSI (14 period)
     │    ├─► MACD (12, 26, 9)
     │    ├─► Bollinger Bands (20, 2)
     │    ├─► EMA (12, 26 periods)
     │    ├─► ATR (14 period)
     │    └─► SMA (20, 50 periods)
     │
     └─► Fallback: custom numpy implementations
     │
Output: DataFrame with indicator columns
```

#### Indicator Specifications

| Indicator | Column Names | Parameters | Purpose |
|-----------|-------------|------------|---------|
| RSI | `RSI` | timeperiod=14 | Momentum oscillator |
| MACD | `MACD`, `MACD_Signal`, `MACD_Hist` | fast=12, slow=26, signal=9 | Trend following |
| Bollinger Bands | `BB_Upper`, `BB_Middle`, `BB_Lower` | timeperiod=20, nbdev=2 | Volatility bands |
| EMA | `EMA_12`, `EMA_26` | timeperiod=12/26 | Exponential MA |
| ATR | `ATR` | timeperiod=14 | Volatility measure |
| SMA | `SMA_20`, `SMA_50` | timeperiod=20/50 | Simple MA |

#### Fallback Strategy
When `pandas_ta` is not installed:
1. Catches `ImportError`
2. Logs warning message
3. Uses custom numpy-based implementations from `src.technical_indicators`
4. Continues pipeline execution

**Fallback Indicators**: Basic moving averages and momentum calculations using numpy.

#### State Management
- `indicators`: Dict mapping indicator names to Series
- Updated after each evaluation
- Can be queried for specific indicator values

### Design Patterns Used
- **Strategy Pattern**: Swappable indicator computation backends
- **Decorator Pattern**: Adds indicators to existing DataFrame
- **Fallback Pattern**: Graceful degradation when dependencies missing

### Extension Points
- Add new technical indicators
- Implement custom indicator libraries
- Add machine learning features
- Optimize computation for real-time use

---

## 4. Module: `src.strategy`

### Purpose
Signal generation module that evaluates technical indicators and produces trading signals using configurable strategies.

### Dependencies
- `pandas` (DataFrame operations)
- `numpy` (numerical computations)
- `dataclasses` (TradeSignal definition)

### Class: `TradeSignal`

#### Dataclass Definition
```python
@dataclass
class TradeSignal:
    symbol: str                               # Stock symbol
    action: str                               # BUY, SELL, or HOLD
    confidence: float = 0.0                   # Signal strength (0-1)
    timestamp: datetime = field(default_factory=datetime.now)
    price: Optional[float] = None             # Execution price
    volume: Optional[int] = None              # Trade volume
    metadata: Dict[str, Any] = field(default_factory=dict)   # Context
```

#### Action Types
| Action | Description | Typical Use Case |
|--------|-------------|------------------|
| `BUY` | Buy signal | Bullish conditions detected |
| `SELL` | Sell signal | Bearish conditions detected |
| `HOLD` | No action | Neutral/unclear conditions |

#### Confidence Score
- Range: 0.0 to 1.0
- Higher values indicate stronger signal conviction
- Used by strategy voting mechanism
- Can filter signals below threshold

### Class: `SignalGenerator`

#### Responsibilities
1. Evaluate technical indicators against strategy rules
2. Generate trading signals based on strategy logic
3. Enforce cooldown between signals
4. Support multiple strategies with voting mechanism
5. Track signal history and timing

#### Configuration Structure
```python
{
       'strategies': ['rsi_macd'],               # Enabled strategies
       'thresholds': {                            # Strategy thresholds
           'rsi_overbought': 70,
           'rsi_oversold': 30,
           'macd_cross_threshold': 0.0
       },
       'cooldown_seconds': 60,                   # Min time between signals
       'min_confidence': 0.5                     # Minimum confidence to act
}
```

#### Strategy: RSI + MACD

**Logic Flow**:
```
1. Get latest bar data with indicators
2. Check cooldown period
3. Evaluate RSI conditions:
    - RSI < oversold (e.g., 30) → Bullish momentum
    - RSI > overbought (e.g., 70) → Bearish momentum
4. Evaluate MACD conditions:
    - MACD > Signal + histogram > 0 → Bullish crossover
    - MACD < Signal + histogram < 0 → Bearish crossover
5. Combine signals:
    - Both bullish → BUY with high confidence
    - Both bearish → SELL with high confidence
    - Mixed → HOLD (wait for confirmation)
6. Calculate confidence based on indicator agreement
```

**Signal Generation Rules**:
| RSI Condition | MACD Condition | Result |
|---------------|----------------|--------|
| Oversold (<30) | Bullish crossover | **BUY** (high confidence) |
| Overbought (>70) | Bearish crossover | **SELL** (high confidence) |
| Oversold (<30) | Neutral | **HOLD** |
| Overbought (>70) | Neutral | **HOLD** |
| Neutral | Bullish crossover | **HOLD** |
| Neutral | Bearish crossover | **HOLD** |

#### Cooldown Mechanism
- Prevents excessive trading signals
- Configurable cooldown period (default: 60 seconds)
- Checked before signal generation
- Returns HOLD during cooldown period

**Implementation**:
```python
def _is_in_cooldown(self) -> bool:
    if self.last_signal_time is None:
        return False
    elapsed = (datetime.now() - self.last_signal_time).total_seconds()
    return elapsed < self.signal_cooldown
```

#### Voting Mechanism (Future)
- Supports multiple strategies simultaneously
- Each strategy votes BUY, SELL, or HOLD
- Majority vote determines final signal
- Tie-breaking based on confidence scores

### Design Patterns Used
- **Strategy Pattern**: Swappable trading strategies
- **Template Method**: Standardized signal generation flow
- **Guard Clause**: Cooldown check prevents unnecessary computation

### Extension Points
- Add new strategy implementations
- Implement custom voting algorithms
- Add machine learning model integration
- Support for order types (limit, stop-loss)

---

## 5. Module: `src.dispatcher`

### Purpose
Signal dispatch module that sends trading signals to execution interfaces with resilience features.

### Dependencies
- `requests` (HTTP client)
- `json` (payload serialization)
- `time` (retry delay)
- `dataclasses` (DispatchResult definition)

### Class: `DispatchResult`

#### Dataclass Definition
```python
@dataclass
class DispatchResult:
    success: bool                               # Success status
    status_code: Optional[int] = None           # HTTP status code
    response_data: Optional[Dict[str, Any]] = None   # Response body
    error_message: Optional[str] = None         # Error details
    timestamp: datetime = field(default_factory=datetime.now)
```

### Class: `SignalDispatcher`

#### Responsibilities
1. Execute trading signals via broker API
2. Fallback to webhook if API fails
3. Implement circuit breaker pattern
4. Handle retries with exponential backoff
5. Track failure counts and state

#### Execution Interfaces

| Interface | Method | Use Case |
|-----------|--------|----------|
| Broker API | HTTP POST to `execution_url` | Primary execution |
| Webhook | HTTP POST to `webhook_url` | Fallback execution |

#### Circuit Breaker Pattern
```
State: circuit_open = False
     │
     ├─► On Success:
     │       failure_count = 0
     │       circuit_open = False
     │
     └─► On Failure:
            failure_count += 1
            if failure_count >= threshold:
                circuit_open = True
```

**Configuration**:
- `circuit_breaker_threshold`: Failures before opening (default: 5)
- Automatically resets on successful dispatch
- Prevents cascading failures

#### Retry Logic
```python
for attempt in range(self.max_retries):
    try:
        response = requests.post(url, json=payload, ...)
        if response.status_code in [200, 201]:
            return success_result
         # Otherwise retry after delay
         time.sleep(self.retry_delay)
```

**Configuration**:
- `max_retries`: Maximum retry attempts (default: 3)
- `retry_delay`: Delay between retries in seconds (default: 1.0)
- Exponential backoff for consecutive failures

### Design Patterns Used
- **Adapter Pattern**: Multiple execution interfaces
- **Circuit Breaker Pattern**: Prevents cascading failures
- **Retry Pattern**: Automatic recovery from transient errors

### Extension Points
- Add new execution interfaces (e.g., WebSocket, message queue)
- Implement custom retry strategies
- Add order tracking and confirmation handling

---

## 6. Module: `src.utils`

### Purpose
Helper functions for configuration loading, logging setup, and common utilities.

### Dependencies
- `yaml` (YAML parsing)
- `logging` (Python standard library)
- `os` (environment variable access)

### Functions

#### `load_config(config_path: str) -> Dict[str, Any]`

Load configuration from YAML file.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `config_path` | `str` | Path to YAML config file |

**Returns**: `Dict[str, Any]` - Parsed configuration dictionary

**Example**:
```python
from src.utils import load_config

config = load_config('config/strategies.yaml')
print(config['strategies'])
```

#### `setup_logging(level: str = "INFO") -> None`

Configure logging for the application.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `level` | `str` | Logging level (DEBUG, INFO, WARNING, ERROR) |

**Configured Handlers**:
- Console handler with colored output
- File handler for persistent logging

### Design Patterns Used
- **Factory Pattern**: Configuration loading
- **Singleton Pattern**: Logger instance

---

## 7. Module: `backtest`

### Purpose
Backtesting module that runs historical strategy simulations using OHLCV data.

### Dependencies
- `pandas` (DataFrame operations)
- `src.agent.TradingAgent` (pipeline execution)
- `src.strategy.TradeSignal` (signal tracking)

### Class: `BacktestRunner`

#### Responsibilities
1. Load historical market data
2. Execute trading pipeline on each bar
3. Track signal performance
4. Generate backtest report

#### Backtest Flow
```
Input:  Historical OHLCV DataFrame
     │
     ├─► For each bar in DataFrame:
     │       └─► TradingAgent.run_pipeline(bar)
     │
     ├─► Collect all signals
     ├─► Calculate performance metrics
     │       - Total trades
     │       - Win rate
     │       - Average profit/loss
     │       - Sharpe ratio
     │
     └─► Output: Backtest report
```

### Design Patterns Used
- **Iterator Pattern**: Sequential bar processing
- **Reporter Pattern**: Performance metrics generation

---

## 8. Module: `database.config` (v2.0)

### Purpose
PostgreSQL connection configuration and SQLAlchemy setup for the trading agent system.

### Dependencies
- `sqlalchemy` (ORM framework)
- `psycopg2` (PostgreSQL driver)
- `pydantic` (settings validation)
- `python-dotenv` (environment variables)

### Class: `DatabaseConfig`

#### Configuration Settings
| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `DATABASE_URL` | `str` | `postgresql://...` | PostgreSQL connection string |
| `POOL_SIZE` | `int` | `10` | Persistent connections |
| `MAX_OVERFLOW` | `int` | `20` | Additional connections under load |
| `POOL_TIMEOUT` | `int` | `30` | Seconds to wait for connection |
| `POOL_RECYCLE` | `int` | `3600` | Connection lifetime in seconds |

### Functions

#### `get_engine() -> Engine`

Get the database engine with connection pool.

**Returns**: `Engine` - SQLAlchemy engine instance

**Configuration**:
- `pool_size`: 10 (persistent connections)
- `max_overflow`: 20 (additional connections under load)
- `pool_timeout`: 30 seconds
- `pool_recycle`: 3600 seconds (1 hour)

#### `get_session() -> Session`

Create a new database session.

**Returns**: `Session` - SQLAlchemy session instance

#### `init_db()`

Initialize database schema (create all tables).

**Usage**:
```python
from database.config import init_db
init_db()
```

#### `get_db()`

FastAPI dependency injector for database sessions.

**Usage**:
```python
from fastapi import Depends
from database.config import get_db

@app.get("/api/signals")
def list_signals(db: Session = Depends(get_db)):
    return db.query(Signal).all()
```

### Design Patterns Used
- **Factory Pattern**: Session creation
- **Dependency Injection**: Database session for FastAPI routes
- **Configuration Pattern**: Environment-based settings

---

## 9. Module: `database.models` (v2.0)

### Purpose
SQLAlchemy ORM models for the trading agent database schema. Normalized design for extensible metadata storage.

### Dependencies
- `sqlalchemy` (ORM framework)
- `datetime` (timestamp handling)
- `json` (metadata storage)

### Models Overview

| Model | Table | Purpose |
|-------|-------|---------|
| `Watchlist` | `watchlist` | Active stocks to monitor |
| `Signal` | `signal` | Generated trading signals |
| `PriceData` | `price_data` | Historical OHLCV data |
| `SystemLog` | `system_log` | Activity logging |
| `ScannerConfig` | `scanner_config` | Runtime configuration |

### Design Patterns Used
- **Table-per-Class Pattern**: Each model maps to one table
- **JSON Column Pattern**: Extensible metadata storage
- **Auditable Pattern**: Created/updated timestamps

---

## 10. Module: `services.scanner` (v2.0)

### Purpose
Multi-threaded scanner service that continuously monitors the watchlist and generates trading signals. Designed for 24/7 operation with automated error recovery.

### Dependencies
- `concurrent.futures.ThreadPoolExecutor` (parallel scanning)
- `database.models.Watchlist`, `Signal`, `SystemLog`, `ScannerConfig`
- `src.technical_indicators.Indicators` (indicator computation)
- `vnstock.Quote` (market data API)

### Class: `ScannerService`

#### Responsibilities
1. Load and manage watchlist from database
2. Scan all stocks in parallel using thread pool
3. Compute technical indicators for each stock
4. Generate trading signals based on indicator values
5. Persist signals to database
6. Log all scanner activities
7. Reload configuration periodically
8. Provide graceful shutdown

#### State Management
| Attribute | Type | Purpose |
|-----------|------|---------|
| `max_workers` | `int` | Thread pool size |
| `executor` | `ThreadPoolExecutor` | Parallel scanning |
| `running` | `bool` | Scanner running state |
| `watchlist` | `List[Watchlist]` | Active stocks |
| `config` | `Dict[str, str]` | Runtime config |
| `_lock` | `threading.Lock` | Thread safety |

#### Scanner Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `scan_interval` | 30s | Default scan interval |
| `high_priority_interval` | 10s | VN30 stocks |
| `low_priority_interval` | 60s | Other stocks |
| `max_workers` | 10 | Thread pool size |

#### Pipeline Execution Flow
```
run() loop:
     │
     ├─► reload_config()                    # Update settings
     ├─► load_watchlist(db)                 # Get active stocks
     │
     ├─► For each stock in watchlist:
     │       └─► scan_stock(stock)          # Parallel execution
     │               ├─► _fetch_historical_data()   # vnstock API
     │               ├─► Compute indicators (RSI, MACD)
     │               ├─► _evaluate_signals()         # Generate signal
     │               └─► _save_signal()                # Persist to DB
     │
     ├─► Wait for all scans to complete
     ├─► Sleep for scan_interval
     └─► Repeat
```

#### Error Handling
- **Connection Errors**: Logged to SystemLog, scanner continues
- **Calculation Failures**: Logged with symbol details, next stock scanned
- **Database Errors**: Transaction rollback, retry on next cycle
- **Graceful Shutdown**: ThreadPoolExecutor waits for running tasks

### Singleton Pattern

```python
def get_scanner() -> ScannerService:
    """Get or create scanner singleton"""
    global scanner_instance
    if scanner_instance is None:
        scanner_instance = ScannerService()
    return scanner_instance
```

### Design Patterns Used
- **Thread Pool Pattern**: Parallel stock scanning
- **Singleton Pattern**: Single scanner instance
- **Observer Pattern**: Configuration reload triggers update
- **Circuit Breaker Pattern**: Error recovery for API calls

---

## 11. Module: `api` (FastAPI) (v2.0)

### Purpose
RESTful API backend for signal CRUD operations, watchlist management, and scanner control.

### Dependencies
- `fastapi` (web framework)
- `pydantic` (request/response validation)
- `sqlalchemy` (database access)
- `database.models` (ORM models)
- `services.scanner` (scanner control)

### API Endpoints Overview

#### Signals
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/signals` | List all signals (with filters) |
| GET | `/api/signals/{id}` | Get signal details |
| POST | `/api/signals` | Create new signal (manual) |
| DELETE | `/api/signals/{id}` | Delete signal |

#### Watchlist
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/watchlist` | List all watchlist stocks |
| POST | `/api/watchlist` | Add stock to watchlist |
| PUT | `/api/watchlist/{id}` | Update stock config |
| DELETE | `/api/watchlist/{id}` | Remove from watchlist |

#### Scanner
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/scanner/status` | Get scanner status |
| POST | `/api/scanner/start` | Start scanning |
| POST | `/api/scanner/stop` | Stop scanning |
| POST | `/api/scanner/scan/{symbol}` | Scan single stock |

### Design Patterns Used
- **RESTful Pattern**: Resource-oriented URLs
- **Dependency Injection**: Database sessions via FastAPI Depends
- **Validation Pattern**: Pydantic models for request/response
- **CORS Pattern**: Cross-origin support for frontend

---

## 12. Module: `dashboard` (Streamlit) (v2.0)

### Purpose
Web-based management dashboard for monitoring signals, managing watchlist, and viewing analytics.

### Dependencies
- `streamlit` (web framework)
- `pandas` (data manipulation)
- `plotly` (interactive charts)
- `database.config` (database access)
- `database.models` (ORM models)
- `api` (REST API calls, optional)

### Dashboard Features

#### Signal Monitoring
- Real-time signal feed with auto-refresh
- Filter by symbol, date range, signal type, confidence
- Sort by timestamp, confidence score, price
- Detailed signal view with indicator values

#### Watchlist Management
- View all watchlist stocks
- Add/remove stocks from watchlist
- Edit stock configuration (name, sector, priority)
- Enable/disable stocks without deletion

#### Analytics Dashboard
- Signal performance over time
- Win/loss ratio by symbol
- Confidence distribution histogram
- Signal frequency by type (BUY/SELL/HOLD)

#### Scanner Control
- View scanner status (running/stopped)
- Start/stop scanner service
- Trigger manual scan for single stock
- View scanner logs and errors

### Design Patterns Used
- **Page Layout Pattern**: Multi-page navigation
- **State Management Pattern**: Session state for filters
- **Auto-Refresh Pattern**: Periodic data reload
- **Responsive Layout Pattern**: Adaptive grid components

---

## System Integration Overview

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│ Streamlit      │◀──────▶│ FastAPI        │◀──────▶│ PostgreSQL      │
│ Dashboard      │         │ Backend API    │         │ Database        │
└──────────────┘         └──────────────┘         └──────────────┘
                                  ▲
                                  │
                          ┌──────────────┐
                          │ Scanner          │
                          │ Service          │
                          └──────────────┘
                                  │
                                  ▼
                          ┌──────────────┐
                          │ vnstock API    │
                          │ Market Data    │
                          └──────────────┘
```

**Data Flow**:
1. **Scanner Service** continuously monitors watchlist and generates signals
2. Signals are persisted to **PostgreSQL** database
3. **FastAPI Backend** provides REST endpoints for CRUD operations
4. **Streamlit Dashboard** consumes API/data for real-time monitoring
5. User interactions flow: Dashboard → FastAPI → Database/Scanner

---

**Version:** 2.0.0  
**Last Updated:** 2026-06-15
