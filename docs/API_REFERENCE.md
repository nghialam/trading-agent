# API Reference

## Autonomous Trading Agent - Scalable 24/7 System

**Version:** 2.0.0  
**Date:** 2026-06-15  

---

## Table of Contents

### Core Components
1. [TradingAgent](#tradingagent)
2. [DataScanner](#datascanner)
3. [EvaluationEngine](#evaluationengine)
4. [SignalGenerator](#signalgenerator)
5. [TradeSignal](#tradesignal)
6. [SignalDispatcher](#signaldispatcher)
7. [BacktestRunner](#backtestrunner)

### New Components (v2.0)
8. [ScannerService](#scannerservice)
9. [Watchlist Model](#watchlist-model)
10. [Signal Model](#signal-model)
11. [PriceData Model](#pricedata-model)
12. [SystemLog Model](#systemlog-model)
13. [ScannerConfig Model](#scannerconfig-model)
14. [Database Configuration](#database-configuration)

---

## Core Components

### TradingAgent

**File**: `src/agent.py`  
**Module**: `src.agent`  

Main orchestrator class that coordinates the four-stage trading pipeline.

#### Class Definition

```python
class TradingAgent:
    """
    Main Trading Agent that orchestrates the four-stage pipeline:
        1. Market Scanning
        2. Evaluation
        3. Signal Generation
        4. Signal Dispatch
    """
```

#### Constructor

```python
def __init__(self, symbol: str = "VNM", strategy_config: Optional[str] = None)
```

**Parameters**:
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `symbol` | `str` | `"VNM"` | Stock symbol to trade |
| `strategy_config` | `Optional[str]` | `None` | Path to YAML strategy config file |

**Attributes**:
| Name | Type | Description |
|------|------|-------------|
| `symbol` | `str` | Trading symbol |
| `scanner` | `DataScanner` | Market data scanner instance |
| `evaluator` | `EvaluationEngine` | Technical analysis engine instance |
| `generator` | `SignalGenerator` | Signal generator instance |
| `dispatcher` | `SignalDispatcher` | Signal dispatcher instance |
| `is_running` | `bool` | Trading state flag |
| `signals_received` | `list` | History of received signals |
| `trades_executed` | `list` | History of executed trades |

#### Methods

##### `run_pipeline(bar_data: pd.DataFrame) -> Optional[TradeSignal]`

Execute the full pipeline for a single bar of data.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `bar_data` | `pd.DataFrame` | DataFrame with OHLCV data |

**Returns**: `Optional[TradeSignal]` - TradeSignal if BUY/SELL, else None (HOLD)

**Pipeline Steps**:
1. Scan/Validate Data → `self.scanner.scan()`
2. Evaluate Technical Indicators → `self.evaluator.evaluate()`
3. Generate Signal → `self.generator.generate_signal()`
4. Dispatch Signal → `self.dispatcher.dispatch()` (if BUY/SELL)

**Example**:
```python
from src.agent import TradingAgent

agent = TradingAgent(symbol='VNM')
signal = agent.run_pipeline(bar_data)
if signal and signal.action == "BUY":
    print(f"Buy signal at {signal.price}")
```

---

### DataScanner

**File**: `src/scanning.py`  
**Module**: `src.scanning`  

Market data scanning layer that ingests and validates market data.

#### Class Definition

```python
class DataScanner:
    """
    Market Scanner that ingests raw market data
    Uses vnstock for Vietnamese market data access
    """
```

#### Constructor

```python
def __init__(self, symbol: str)
```

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `symbol` | `str` | Stock symbol to scan |

**Attributes**:
| Name | Type | Description |
|------|------|-------------|
| `symbol` | `str` | Trading symbol |
| `data_cache` | `Optional[pd.DataFrame]` | Cache of last valid data |

#### Methods

##### `scan(raw_data: pd.DataFrame) -> pd.DataFrame`

Scan and validate incoming market data.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `raw_data` | `pd.DataFrame` | Raw OHLCV DataFrame from data source |

**Returns**: `pd.DataFrame` - Validated DataFrame ready for evaluation

**Raises**:
| Exception | Condition |
|-----------|-----------|
| `ValueError` | If data is empty or missing required columns |

**Validation Rules**:
- Data must not be empty
- Required columns: `open`, `high`, `low`, `close`, `volume`

**Example**:
```python
from src.scanning import DataScanner

scanner = DataScanner(symbol='VNM')
validated_data = scanner.scan(raw_ohlcv_data)
```

---

### EvaluationEngine

**File**: `src/evaluation.py`  
**Module**: `src.evaluation`  

Computes technical indicators from raw market data using pandas-ta or custom implementations.

#### Class Definition

```python
class EvaluationEngine:
    """
    Computes technical indicators from raw market data
    Uses pandas-ta or custom numpy-based implementations
    """
```

#### Constructor

```python
def __init__(self, symbol: str)
```

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `symbol` | `str` | Stock symbol to evaluate |

**Attributes**:
| Name | Type | Description |
|------|------|-------------|
| `symbol` | `str` | Trading symbol |
| `indicators` | `Dict[str, pd.Series]` | Computed indicator series |

#### Methods

##### `evaluate(data: pd.DataFrame) -> pd.DataFrame`

Compute all technical indicators on the input data.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `data` | `pd.DataFrame` | DataFrame with OHLCV columns |

**Returns**: `pd.DataFrame` - DataFrame with added indicator columns

**Raises**:
| Exception | Condition |
|-----------|-----------|
| `ValueError` | If data is empty |

##### `_compute_indicators(df: pd.DataFrame) -> pd.DataFrame`

Internal method to compute all technical indicators.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `df` | `pd.DataFrame` | DataFrame with OHLCV data |

**Returns**: `pd.DataFrame` - DataFrame with added indicators

**Computed Indicators**:
| Indicator | Column Name | Parameters |
|-----------|-------------|------------|
| RSI | `RSI` | 14 period |
| MACD Line | `MACD` | 12, 26, 9 |
| MACD Signal | `MACD_Signal` | 12, 26, 9 |
| MACD Histogram | `MACD_Hist` | 12, 26, 9 |
| Bollinger Upper | `BB_Upper` | 20 period, 2 std |
| Bollinger Middle | `BB_Middle` | 20 period, 2 std |
| Bollinger Lower | `BB_Lower` | 20 period, 2 std |
| EMA 12 | `EMA_12` | 12 period |
| EMA 26 | `EMA_26` | 26 period |
| ATR | `ATR` | 14 period |
| SMA 20 | `SMA_20` | 20 period |
| SMA 50 | `SMA_50` | 50 period |

**Fallback Behavior**: If `pandas-ta` is not installed, uses custom numpy-based implementations from `src.technical_indicators`.

---

### SignalGenerator

**File**: `src/strategy.py`  
**Module**: `src.strategy`  

Generates trading signals based on technical indicators with configurable strategies.

#### Class Definition

```python
class SignalGenerator:
    """
    Generates trading signals based on technical indicators
    Supports multiple strategies with configurable parameters
    """
```

#### Constructor

```python
def __init__(self, symbol: str, config: Optional[Dict[str, Any]] = None)
```

**Parameters**:
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `symbol` | `str` | - | Stock symbol |
| `config` | `Optional[Dict[str, Any]]` | `{}` | Strategy configuration |

**Default Configuration**:
```python
{
    'strategies': ['rsi_macd'],
    'thresholds': {
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'macd_cross_threshold': 0.0
    },
    'cooldown_seconds': 60,
    'min_confidence': 0.5
}
```

**Attributes**:
| Name | Type | Description |
|------|------|-------------|
| `symbol` | `str` | Trading symbol |
| `config` | `Dict[str, Any]` | Strategy configuration |
| `last_signal_time` | `Optional[datetime]` | Timestamp of last signal |
| `signal_cooldown` | `int` | Cooldown period in seconds |

#### Methods

##### `generate_signal(evaluated_data: pd.DataFrame) -> Optional[TradeSignal]`

Generate a trading signal from evaluated data.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `evaluated_data` | `pd.DataFrame` | DataFrame with technical indicators |

**Returns**: `Optional[TradeSignal]` - TradeSignal if BUY/SELL, else None (HOLD)

**Workflow**:
1. Check for empty data
2. Check cooldown period
3. Evaluate all enabled strategies
4. Use voting mechanism for multiple strategies
5. Return final signal

##### `_is_in_cooldown() -> bool`

Check if we're in cooldown period.

**Returns**: `bool` - True if in cooldown, False otherwise

##### `_evaluate_rsi_macd(latest: pd.Series) -> Dict[str, Any]`

Evaluate RSI + MACD strategy.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `latest` | `pd.Series` | Latest bar data with indicators |

**Returns**: `Dict[str, Any]` - Dictionary with action and confidence

---

### TradeSignal

**File**: `src/strategy.py`  
**Module**: `src.strategy`  

Dataclass representing a trading signal.

#### Class Definition

```python
@dataclass
class TradeSignal:
    """Represents a trading signal"""
    symbol: str
    action: str     # BUY, SELL, HOLD
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    price: Optional[float] = None
    volume: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `symbol` | `str` | Required | Stock symbol |
| `action` | `str` | Required | Trading action: BUY, SELL, or HOLD |
| `confidence` | `float` | `0.0` | Signal confidence (0.0 - 1.0) |
| `timestamp` | `datetime` | `now()` | Signal generation time |
| `price` | `Optional[float]` | `None` | Execution price |
| `volume` | `Optional[int]` | `None` | Trade volume |
| `metadata` | `Dict[str, Any]` | `{}` | Additional context |

**Example**:
```python
from src.strategy import TradeSignal
from datetime import datetime

signal = TradeSignal(
    symbol='VNM',
    action='BUY',
    confidence=0.85,
    price=28.50,
    volume=1000,
    metadata={'strategy': 'rsi_macd', 'reason': 'oversold_reversal'}
)
```

---

### SignalDispatcher

**File**: `src/dispatcher.py`  
**Module**: `src.dispatcher`  

Sends trading signals to execution interfaces (broker API or webhook).

#### Class Definition

```python
class SignalDispatcher:
    """Dispatches trading signals to configured execution interfaces"""
```

#### Constructor

```python
def __init__(self, config: Dict[str, Any])
```

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `config` | `Dict[str, Any]` | Execution configuration |

#### Methods

##### `dispatch(signal: TradeSignal) -> DispatchResult`

Execute a trading signal via configured interfaces.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `signal` | `TradeSignal` | Trading signal to execute |

**Returns**: `DispatchResult` - Execution result with status and details

**Execution Flow**:
1. Check circuit breaker state
2. Try broker API (primary)
3. Fallback to webhook (secondary)
4. Update circuit breaker on success/failure
5. Return dispatch result

---

### DispatchResult

**File**: `src/dispatcher.py`  
**Module**: `src.dispatcher`  

Dataclass representing a dispatch execution result.

#### Class Definition

```python
@dataclass
class DispatchResult:
    success: bool
    status_code: Optional[int] = None
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
```

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `success` | `bool` | Required | Whether dispatch succeeded |
| `status_code` | `Optional[int]` | `None` | HTTP status code |
| `response_data` | `Optional[Dict]` | `None` | Response body |
| `error_message` | `Optional[str]` | `None` | Error details |
| `timestamp` | `datetime` | `now()` | Dispatch time |

---

### BacktestRunner

**File**: `backtest/runner.py`  
**Module**: `backtest.runner`  

Runs backtesting simulations using historical market data.

#### Class Definition

```python
class BacktestRunner:
    """Runs backtesting simulations with configurable parameters"""
```

#### Methods

##### `run(symbol: str, start_date: str, end_date: str) -> Dict[str, Any]`

Run backtest for a given symbol and date range.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `symbol` | `str` | Stock symbol |
| `start_date` | `str` | Start date (YYYY-MM-DD) |
| `end_date` | `str` | End date (YYYY-MM-DD) |

**Returns**: `Dict[str, Any]` - Backtest results with performance metrics

---

## New Components (v2.0)

### ScannerService

**File**: `services/scanner.py`  
**Module**: `services.scanner`  

Multi-threaded scanner service that continuously monitors the watchlist and generates trading signals. Designed for 24/7 operation with automated error recovery.

#### Class Definition

```python
class ScannerService:
    """
    Main scanner service that monitors stocks and generates trading signals.
    
    Features:
        - Multi-threaded scanning for watchlist
        - Priority-based update frequency (VN30 high priority)
        - Automated error recovery with retry logic
        - Real-time configuration reload
    """
```

#### Constructor

```python
def __init__(self, max_workers: int = 10)
```

**Parameters**:
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `max_workers` | `int` | `10` | Number of threads in pool |

**Attributes**:
| Name | Type | Description |
|------|------|-------------|
| `max_workers` | `int` | Thread pool size |
| `executor` | `ThreadPoolExecutor` | Thread pool executor |
| `running` | `bool` | Scanner running state |
| `watchlist` | `List[Watchlist]` | Active watchlist from database |
| `config` | `Dict[str, str]` | Runtime configuration |
| `_lock` | `threading.Lock` | Thread safety lock |

#### Methods

##### `load_watchlist(db_session) -> List[Watchlist]`

Load active watchlist from database.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `db_session` | `Session` | Database session |

**Returns**: `List[Watchlist]` - Active stocks to monitor

##### `load_config(db_session) -> Dict[str, str]`

Load scanner configuration from database.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `db_session` | `Session` | Database session |

**Returns**: `Dict[str, str]` - Configuration key-value pairs

##### `reload_config()`

Reload configuration from database (call periodically).

##### `scan_stock(stock: Watchlist)`

Scan a single stock and generate signals. Runs in separate thread for parallel processing.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `stock` | `Watchlist` | Stock to scan |

**Workflow**:
1. Fetch historical data from vnstock API
2. Compute technical indicators (RSI, MACD)
3. Evaluate signals based on indicator values
4. Save generated signal to database
5. Log any errors that occur

##### `_fetch_historical_data(symbol: str, days: int = 30) -> pd.DataFrame`

Fetch historical OHLCV data from vnstock API.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `symbol` | `str` | Stock symbol |
| `days` | `int` | Number of days of history |

**Returns**: `pd.DataFrame` - OHLCV DataFrame or empty if failed

##### `_evaluate_signals(rsi: float, macd: float, macd_signal: float, close_price: float) -> tuple`

Evaluate technical indicators to generate trading signals.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `rsi` | `float` | RSI value |
| `macd` | `float` | MACD line value |
| `macd_signal` | `float` | MACD signal line value |
| `close_price` | `float` | Current close price |

**Returns**: `tuple` - `(signal_type: str, confidence: float)`

**Signal Logic**:
| RSI Condition | MACD Condition | Result |
|---------------|----------------|--------|
| < 30 (oversold) | > Signal (bullish) | **BUY** (high confidence) |
| > 70 (overbought) | < Signal (bearish) | **SELL** (high confidence) |
| Otherwise | Any | **HOLD** (neutral) |

##### `_save_signal(symbol: str, signal_type: str, confidence_score: float, price_at_signal: float, indicators: Dict)`

Save trading signal to database.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `symbol` | `str` | Stock symbol |
| `signal_type` | `str` | BUY / SELL / HOLD |
| `confidence_score` | `float` | Signal confidence (0.0 - 1.0) |
| `price_at_signal` | `float` | Price at signal time |
| `indicators` | `Dict` | Technical indicator values |

##### `scan_single_stock(symbol: str)`

Scan a single stock (for manual trigger via API).

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `symbol` | `str` | Stock symbol to scan |

##### `run()`

Main scanner loop. Runs continuously, scanning all watchlist stocks in parallel.

**Workflow**:
1. Reload configuration from database
2. Load active watchlist
3. Scan all stocks in parallel using ThreadPoolExecutor
4. Wait for all scans to complete
5. Sleep for configured interval
6. Repeat

##### `stop()`

Stop the scanner service gracefully. Shuts down thread pool and waits for running tasks.

---

### Watchlist Model

**File**: `database/models.py`  
**Table**: `watchlist`  

Active stocks to monitor in the watchlist.

#### Class Definition

```python
class Watchlist(Base):
    __tablename__ = 'watchlist'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), unique=True, nullable=False)
    name = Column(Text)
    sector = Column(String(50))
    priority = Column(Integer, default=2)  # 1=high (VN30), 2=medium, 3=low
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

#### Columns

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `Integer` | PK, auto-increment | Primary key |
| `symbol` | `String(10)` | Unique, not null | Stock ticker symbol |
| `name` | `Text` | - | Company name |
| `sector` | `String(50)` | - | Industry sector |
| `priority` | `Integer` | Default: 2 | Priority level (1=high, 2=medium, 3=low) |
| `enabled` | `Boolean` | Default: True | Whether stock is active |
| `created_at` | `DateTime` | Default: now | Creation timestamp |
| `updated_at` | `DateTime` | Auto-update | Last update timestamp |

#### Indexes

| Index Name | Columns | Purpose |
|-----------|---------|---------|
| `idx_watchlist_enabled` | `enabled` | Filter active stocks |

---

### Signal Model

**File**: `database/models.py`  
**Table**: `signal`  

Generated trading signals with full metadata and indicator values.

#### Class Definition

```python
class Signal(Base):
    __tablename__ = 'signal'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    signal_type = Column(String(10), nullable=False)  # BUY / SELL / HOLD
    confidence_score = Column(Float)
    price_at_signal = Column(Float)
    indicators = Column(JSON)
    metadata = Column(JSON)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

#### Columns

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `Integer` | PK, auto-increment | Primary key |
| `symbol` | `String(10)` | Not null, indexed | Stock ticker symbol |
| `timestamp` | `DateTime` | Default: now, indexed | Signal generation time |
| `signal_type` | `String(10)` | Not null | BUY / SELL / HOLD |
| `confidence_score` | `Float` | - | Signal confidence (0.0 - 1.0) |
| `price_at_signal` | `Float` | - | Stock price at signal time |
| `indicators` | `JSON` | - | Technical indicator values |
| `metadata` | `JSON` | - | Additional context |
| `processed` | `Boolean` | Default: False | Whether signal was acted upon |
| `created_at` | `DateTime` | Default: now | Creation timestamp |

#### Indexes

| Index Name | Columns | Purpose |
|-----------|---------|---------|
| `idx_signal_symbol_time` | `(symbol, timestamp)` | Query by stock and date range |
| `idx_signal_confidence` | `confidence_score` | Filter by signal strength |
| `idx_signal_type` | `signal_type` | Filter by signal type |

---

### PriceData Model

**File**: `database/models.py`  
**Table**: `price_data`  

Historical OHLCV price data for each stock.

#### Class Definition

```python
class PriceData(Base):
    __tablename__ = 'price_data'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(BigInteger)
```

#### Columns

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `Integer` | PK, auto-increment | Primary key |
| `symbol` | `String(10)` | Not null, indexed | Stock ticker symbol |
| `timestamp` | `DateTime` | Not null, indexed | Data point time |
| `open` | `Float` | - | Opening price |
| `high` | `Float` | - | Highest price |
| `low` | `Float` | - | Lowest price |
| `close` | `Float` | - | Closing price |
| `volume` | `BigInteger` | - | Trading volume |

#### Indexes

| Index Name | Columns | Purpose |
|-----------|---------|---------|
| `idx_price_data_symbol_time` | `(symbol, timestamp)` | Query historical data |

---

### SystemLog Model

**File**: `database/models.py`  
**Table**: `system_log`  

Activity logging for all scanner operations.

#### Class Definition

```python
class SystemLog(Base):
    __tablename__ = 'system_log'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String(10), nullable=False)  # INFO / WARNING / ERROR / DEBUG
    component = Column(String(50))
    message = Column(Text)
    details = Column(JSON)
```

#### Columns

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `Integer` | PK, auto-increment | Primary key |
| `timestamp` | `DateTime` | Default: now, indexed | Log entry time |
| `level` | `String(10)` | Not null | INFO / WARNING / ERROR / DEBUG |
| `component` | `String(50)` | - | Component name |
| `message` | `Text` | - | Log message |
| `details` | `JSON` | - | Additional context |

#### Indexes

| Index Name | Columns | Purpose |
|-----------|---------|---------|
| `idx_systemlog_timestamp` | `timestamp` | Query by date range |
| `idx_systemlog_level` | `level` | Filter by log level |

---

### ScannerConfig Model

**File**: `database/models.py`  
**Table**: `scanner_config`  

Runtime configuration key-value store for scanner parameters.

#### Class Definition

```python
class ScannerConfig(Base):
    __tablename__ = 'scanner_config'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True, nullable=False)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

#### Columns

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `Integer` | PK, auto-increment | Primary key |
| `key` | `String(50)` | Unique, not null | Configuration key |
| `value` | `Text` | - | Configuration value |
| `updated_at` | `DateTime` | Auto-update | Last update timestamp |

---

### Database Configuration

**File**: `database/config.py`  
**Module**: `database.config`  

PostgreSQL connection configuration and SQLAlchemy setup.

#### Functions

##### `get_engine() -> Engine`

Get the database engine with connection pool.

**Returns**: `Engine` - SQLAlchemy engine instance

**Configuration**:
- `pool_size`: 10 (persistent connections)
- `max_overflow`: 20 (additional connections under load)
- `pool_timeout`: 30 seconds
- `pool_recycle`: 3600 seconds (1 hour)

##### `get_session() -> Session`

Create a new database session.

**Returns**: `Session` - SQLAlchemy session instance

##### `init_db()`

Initialize database schema (create all tables).

**Usage**:
```python
from database.config import init_db
init_db()
```

##### `get_db()`

FastAPI dependency injector for database sessions.

**Usage**:
```python
from fastapi import Depends
from database.config import get_db

@app.get("/api/signals")
def list_signals(db: Session = Depends(get_db)):
    return db.query(Signal).all()
```

---

### Scanner Service Singleton

**File**: `services/scanner.py`  
**Function**: `get_scanner()`

Get or create the scanner singleton instance.

**Signature**:
```python
def get_scanner() -> ScannerService
```

**Returns**: `ScannerService` - Singleton scanner instance

**Usage**:
```python
from services.scanner import get_scanner

scanner = get_scanner()
scanner.run()  # Start scanning
```

---

## API Usage Examples

### Scanner Service (24/7 Operation)

```python
from services.scanner import get_scanner

# Get scanner instance
scanner = get_scanner()

# Start continuous scanning
scanner.run()

# Or run in background thread
import threading
thread = threading.Thread(target=scanner.run, daemon=True)
thread.start()

# Stop scanning
scanner.stop()
```

### FastAPI REST Endpoints

```python
from fastapi import FastAPI, Depends, Session
from database.config import get_db
from database.models import Signal

app = FastAPI()

@app.get("/api/signals")
def list_signals(
    symbol: str = None,
    signal_type: str = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List signals with optional filters"""
    query = db.query(Signal)
    if symbol:
        query = query.filter(Signal.symbol == symbol)
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    return query.order_by(Signal.timestamp.desc()).limit(limit).all()

@app.post("/api/scanner/scan/{symbol}")
def scan_stock(symbol: str, db: Session = Depends(get_db)):
    """Manually scan a single stock"""
    from services.scanner import get_scanner
    scanner = get_scanner()
    scanner.scan_single_stock(symbol)
    return {"status": "scanned", "symbol": symbol}
```

### Streamlit Dashboard

```python
import streamlit as st
import pandas as pd
from database.config import SessionLocal
from database.models import Signal, Watchlist

st.title("Trading Agent Dashboard")

# Load signals
db = SessionLocal()
signals = pd.DataFrame([s.__dict__ for s in db.query(Signal).all()])
st.dataframe(signals)

# Watchlist management
watchlist = db.query(Watchlist).filter_by(enabled=True).all()
for stock in watchlist:
    st.write(f"{stock.symbol} - {stock.name}")
```

---

**Version:** 2.0.0  
**Last Updated:** 2026-06-15
