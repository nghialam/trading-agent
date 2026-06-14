# API Reference

## Autonomous Trading Agent - VnStock Ecosystem

**Version:** 1.0.0  
**Date:** 2026-06-14  

---

## Table of Contents

1. [TradingAgent](#tradingagent)
2. [DataScanner](#datascanner)
3. [EvaluationEngine](#evaluationengine)
4. [SignalGenerator](#signalgenerator)
5. [TradeSignal](#tradesignal)
6. [SignalDispatcher](#signaldispatcher)
7. [DispatchResult](#dispatchresult)
8. [BacktestRunner](#backtestrunner)

---

## TradingAgent

**File**: `src/agent.py`  
**Module**: `src.agent`  

Main orchestrator class that coordinates the four-stage trading pipeline.

### Class Definition

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

### Constructor

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

### Methods

#### `run_pipeline(bar_data: pd.DataFrame) -> Optional[TradeSignal]`

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

## DataScanner

**File**: `src/scanning.py`  
**Module**: `src.scanning`  

Market data scanning layer that ingests and validates market data.

### Class Definition

```python
class DataScanner:
    """
    Market Scanner that ingests raw market data
    Uses vnstock for Vietnamese market data access
    """
```

### Constructor

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

### Methods

#### `scan(raw_data: pd.DataFrame) -> pd.DataFrame`

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

## EvaluationEngine

**File**: `src/evaluation.py`  
**Module**: `src.evaluation`  

Computes technical indicators from raw market data using vnstock_ta.

### Class Definition

```python
class EvaluationEngine:
    """
    Computes technical indicators from raw market data
    Uses vnstock_ta for Vietnamese stock market analysis
    """
```

### Constructor

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

### Methods

#### `evaluate(data: pd.DataFrame) -> pd.DataFrame`

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

#### `_compute_indicators(df: pd.DataFrame) -> pd.DataFrame`

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

**Fallback Behavior**: If `vnstock_ta` is not installed, uses numpy-based fallback implementations.

---

## SignalGenerator

**File**: `src/strategy.py`  
**Module**: `src.strategy`  

Generates trading signals based on technical indicators with configurable strategies.

### Class Definition

```python
class SignalGenerator:
    """
    Generates trading signals based on technical indicators
    Supports multiple strategies with configurable parameters
    """
```

### Constructor

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

### Methods

#### `generate_signal(evaluated_data: pd.DataFrame) -> Optional[TradeSignal]`

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

#### `_is_in_cooldown() -> bool`

Check if we're in cooldown period.

**Returns**: `bool` - True if in cooldown, False otherwise

#### `_evaluate_rsi_macd(latest: pd.Series) -> Dict[str, Any]`

Evaluate RSI + MACD strategy.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `latest` | `pd.Series` | Latest bar data with indicators |

**Returns**: `Dict[str, Any]` - Dictionary with action and confidence

---

## TradeSignal

**File**: `src/strategy.py`  
**Module**: `src.strategy`  

Dataclass representing a trading signal.

### Class Definition

```python
@dataclass
class TradeSignal:
    """Represents a trading signal"""
    symbol: str
    action: str    # BUY, SELL, HOLD
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    price: Optional[float] = None
    volume: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### Fields

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

## SignalDispatcher

**File**: `src/dispatcher.py`  
**Module**: `src.dispatcher`  

Sends trading signals to execution interfaces (broker API or webhook).

### Class Definition

```python
class SignalDispatcher:
    """Dispatches trading signals to configured execution interfaces"""
```

### Constructor

```python
def __init__(self, config: Optional[Dict[str, Any]] = None)
```

**Parameters**:
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `config` | `Optional[Dict[str, Any]]` | `{}` | Execution configuration |

**Default Configuration**:
```python
{
     "execution_url": None,
     "api_key": None,
     "secret_key": None,
     "timeout": 10,
     "max_retries": 3,
     "retry_delay": 1.0,
     "webhook_url": None,
     "signature_method": "none"
}
```

**Attributes**:
| Name | Type | Description |
|------|------|-------------|
| `config` | `Dict[str, Any]` | Full configuration dict |
| `execution_url` | `Optional[str]` | Broker API endpoint URL |
| `api_key` | `Optional[str]` | API authentication key |
| `secret_key` | `Optional[str]` | API secret key |
| `timeout` | `int` | Request timeout in seconds |
| `max_retries` | `int` | Maximum retry attempts |
| `retry_delay` | `float` | Delay between retries in seconds |
| `webhook_url` | `Optional[str]` | Webhook endpoint URL |
| `failure_count` | `int` | Current failure count |
| `circuit_breaker_threshold` | `int` | Threshold to open circuit |
| `circuit_open` | `bool` | Circuit breaker state |
| `last_failure_time` | `Optional[datetime]` | Last failure timestamp |

### Methods

#### `dispatch(signal) -> DispatchResult`

Dispatch a trading signal to configured execution interfaces.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `signal` | `TradeSignal` | Trading signal to execute |

**Returns**: `DispatchResult` - Result of dispatch attempt

**Execution Flow**:
1. Check circuit breaker state
2. Build payload from signal
3. Try broker API (with retries)
4. Fallback to webhook if API fails
5. Return result

#### `_build_payload(signal) -> Dict[str, Any]`

Build JSON payload for dispatch.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `signal` | `TradeSignal` | Trading signal |

**Returns**: `Dict[str, Any]` - JSON payload dict

**Payload Structure**:
```python
{
     "action": signal.action,
     "symbol": signal.symbol,
     "timestamp": signal.timestamp.isoformat(),
     "confidence": signal.confidence,
     "price": signal.price,
     "volume": signal.volume,
     "metadata": signal.metadata
}
```

#### `_dispatch_via_api(payload: Dict[str, Any]) -> DispatchResult`

Dispatch via broker API with retry logic.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `payload` | `Dict[str, Any]` | JSON payload |

**Returns**: `DispatchResult` - Result of API call

**Features**:
- Retry up to `max_retries` times
- Exponential backoff with `retry_delay`
- Bearer token authentication
- Circuit breaker state management

#### `_dispatch_via_webhook(payload: Dict[str, Any]) -> DispatchResult`

Dispatch via webhook as fallback.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `payload` | `Dict[str, Any]` | JSON payload |

**Returns**: `DispatchResult` - Result of webhook call

---

## DispatchResult

**File**: `src/dispatcher.py`  
**Module**: `src.dispatcher`  

Dataclass representing the result of a signal dispatch attempt.

### Class Definition

```python
@dataclass
class DispatchResult:
    success: bool
    status_code: Optional[int] = None
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `success` | `bool` | Required | Whether dispatch succeeded |
| `status_code` | `Optional[int]` | `None` | HTTP status code |
| `response_data` | `Optional[Dict[str, Any]]` | `None` | Response body |
| `error_message` | `Optional[str]` | `None` | Error details |
| `timestamp` | `datetime` | `now()` | Dispatch timestamp |

**Example**:
```python
if result.success:
    print(f"Order placed: {result.response_data}")
else:
    print(f"Dispatch failed: {result.error_message}")
```

---

## BacktestRunner

**File**: `backtest/__init__.py`  
**Module**: `backtest`  

Runs backtests using historical data and the trading agent.

### Class Definition

```python
class BacktestRunner:
    """
    Runs backtests using historical data and the trading agent
    Can integrate with vnstock for real market data
    """
```

### Constructor

```python
def __init__(self, agent)
```

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `agent` | `TradingAgent` | Trading agent instance to test |

**Attributes**:
| Name | Type | Description |
|------|------|-------------|
| `agent` | `TradingAgent` | Reference to trading agent |
| `results` | `list` | List of backtest results |

### Methods

#### `run(start_date: str = "2024-01-01", end_date: str = "2024-12-31") -> Dict[str, Any]`

Run backtest on historical data.

**Parameters**:
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `start_date` | `str` | `"2024-01-01"` | Start date for backtest |
| `end_date` | `str` | `"2024-12-31"` | End date for backtest |

**Returns**: `Dict[str, Any]` - Dictionary with backtest results

**Output Structure**:
```python
{
     "symbol": "VNM",
     "start_date": "2024-01-01",
     "end_date": "2024-12-31",
     "total_bars": 1000,
     "total_signals": 50,
     "signals": [
         {"date": "...", "action": "BUY", "price": ..., "confidence": ...},
         ...
     ]
}
```

**Workflow**:
1. Fetch historical data via `_get_historical_data()`
2. Iterate through each bar/candle
3. Run pipeline for each bar
4. Collect signals (BUY/SELL only)
5. Return summary with all signals

#### `_get_historical_data(start_date: str, end_date: str) -> pd.DataFrame`

Fetch historical data (placeholder - use vnstock in production).

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `start_date` | `str` | Start date |
| `end_date` | `str` | End date |

**Returns**: `pd.DataFrame` - DataFrame with OHLCV data

**Production Note**: Replace with:
```python
import vnstock as vs
df = vs.init(self.agent.symbol).quotes(start=start_date, end=end_date)
```

---

## CLI Interface

**File**: `main.py`  

### Command Line Arguments

| Argument | Type | Choices | Default | Description |
|----------|------|---------|---------|-------------|
| `--symbol` | `str` | - | `"VNM"` | Stock symbol to trade |
| `--mode` | `str` | `backtest`, `live` | `"backtest"` | Trading mode |
| `--start-date` | `str` | - | `"2024-01-01"` | Backtest start date |
| `--end-date` | `str` | - | `"2024-12-31"` | Backtest end date |
| `--log-level` | `str` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `"INFO"` | Logging level |

### Usage Examples

```bash
# Run backtest for VNM stock
python main.py --symbol VNM --mode backtest

# Run with custom date range
python main.py --symbol FPT --mode backtest \
     --start-date 2024-01-01 --end-date 2024-12-31

# Run in live trading mode
python main.py --symbol VNM --mode live

# Enable debug logging
python main.py --symbol VNM --mode backtest --log-level DEBUG
```

---

**End of API Reference**
