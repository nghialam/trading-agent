# API Reference

## Autonomous Trading Agent - Scalable 24/7 System

**Version:** 2.1.0  
**Date:** 2026-06-21  
**Changelog:** Added restart endpoint, updated scanner methods, added signal deduplication docs

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

#### Methods (v2.1)

##### `_get_recent_signal_type(symbol: str, minutes: int = 5) -> Optional[str]`

Get the last signal type for a symbol within a time window to prevent duplicates.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `symbol` | `str` | Stock symbol |
| `minutes` | `int` | Time window in minutes (default: 5) |

**Returns**: `Optional[str]` - Signal type if found, None otherwise

**Purpose**: Prevents duplicate signals for the same stock within a short time window.

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

Reload configuration from database (called every 5 minutes).

##### `scan_stock(stock: Watchlist)`

Scan a single stock and generate signals. Runs in separate thread for parallel processing.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `stock` | `Watchlist` | Stock to scan |

**Workflow**:
1. Fetch 1D historical data (90 days) from vnstock API with retry
2. Fetch 1H historical data (5 days) for Pocket Pivot calculation
3. Compute technical indicators (RSI, MACD) on 1D data
4. Calculate Pocket Pivot on 1H data
5. Generate signal based on technical indicators
6. Check for duplicate signals (5-min window)
7. Run LLM analysis to verify signal
8. Save signal to database
9. Generate daily summary (once per day)

##### `_fetch_historical_data(symbol: str, days: int = 90, interval: str = "1D") -> pd.DataFrame`

Fetch historical OHLCV data from vnstock API with retry logic and rate limit handling.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `symbol` | `str` | Stock symbol |
| `days` | `int` | Number of days of history (default: 90) |
| `interval` | `str` | Data interval: "1D" or "1H" |

**Returns**: `pd.DataFrame` - OHLCV DataFrame or empty if failed

**Error Handling**:
- Retries up to 3 times with exponential backoff (5s, 10s, 20s)
- Detects rate limit errors (429, RetryError, ConnectionError)
- Adds jitter to prevent thundering herd

##### `_evaluate_signals(rsi: float, macd: float, macd_signal: float, close_price: float) -> tuple`

Evaluate technical indicators to generate trading signals with improved SELL detection.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `rsi` | `float` | RSI value |
| `macd` | `float` | MACD line value |
| `macd_signal` | `float` | MACD signal line value |
| `close_price` | `float` | Current close price |

**Returns**: `tuple` - `(signal_type: str, confidence: float)`

**Signal Logic (v2.1)**:
| RSI Condition | MACD Condition | Result | Confidence |
|---------------|----------------|--------|------------|
| > 70 (overbought) | < Signal (bearish) | **SELL** (strong) | 0.5+ |
| > 60 (overbought) | < Signal (bearish) | **SELL** (moderate) | 0.35+ |
| > 45 | < Signal (bearish) | **SELL** (mild) | 0.25+ |
| < 30 (oversold) | > Signal (bullish) | **BUY** (strong) | 0.5+ |
| < 40 (oversold) | > Signal (bullish) | **BUY** (moderate) | 0.35+ |
| < 55 | > Signal (bullish) | **BUY** (mild) | 0.25+ |
| Otherwise | Any | **HOLD** | 0.0-0.3 |

##### `_save_signal(symbol: str, signal_type: str, confidence_score: float, price_at_signal: float, indicators: Dict, llm_verdict: Optional[Dict] = None) -> Optional[int]`

Save trading signal to database.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `symbol` | `str` | Stock symbol |
| `signal_type` | `str` | BUY / SELL / HOLD |
| `confidence_score` | `float` | Signal confidence (0.0 - 1.0) |
| `price_at_signal` | `float` | Price at signal time |
| `indicators` | `Dict` | Technical indicator values |
| `llm_verdict` | `Optional[Dict]` | LLM analysis result |

**Returns**: `Optional[int]` - Signal ID if saved, None on failure

##### `_generate_daily_summary(symbol: str, df_1d: pd.DataFrame, signal_type: str) -> bool`

Generate daily price summary for a stock (once per day).

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `symbol` | `str` | Stock symbol |
| `df_1d` | `pd.DataFrame` | Daily OHLCV data |
| `signal_type` | `str` | Latest signal type |

**Returns**: `bool` - True if created, False if already exists

**Unique Constraint**: `(date, symbol)` - One summary per stock per day

##### `scan_single_stock(symbol: str)`

Scan a single stock (for manual trigger via API).

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `symbol` | `str` | Stock symbol to scan |

##### `run()`

Main scanner loop. Runs continuously, scanning all watchlist stocks in parallel with enhanced error handling.

**Workflow (v2.1)**:
1. Reload configuration from database (every 5 min)
2. Load active watchlist
3. Scan all stocks in parallel using ThreadPoolExecutor
4. Handle executor failures with automatic recreation
5. Wait for all scans (with 60s timeout per scan)
6. Log failed scans (auto-retry next cycle)
7. Sleep for configured interval
8. Repeat

**Error Resilience**:
- Thread failures caught and logged, never crash the loop
- Database constraint violations handled gracefully
- API rate limits trigger exponential backoff

##### `stop()`

Stop the scanner service gracefully. Shuts down thread pool and cancels pending futures.

##### `restart()`

Restart the scanner with a fresh executor while maintaining running state.
```
