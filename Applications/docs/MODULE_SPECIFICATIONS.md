# Module Specifications

## Autonomous Trading Agent - VnStock Ecosystem

**Version:** 1.0.0  
**Date:** 2026-06-14  

---

## Table of Contents

1. [Module: src.agent](#1-module-srcagent)
2. [Module: src.scanning](#2-module-srcscanning)
3. [Module: src.evaluation](#3-module-srcevaluation)
4. [Module: src.strategy](#4-module-srcstrategy)
5. [Module: src.dispatcher](#5-module-srcdispatcher)
6. [Module: src.utils](#6-module-srcutils)
7. [Module: backtest](#7-module-backtest)
8. [Module: config](#8-module-config)

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
    ├─► scanner.scan(bar_data)           # Validate data
    │
    ├─► evaluator.evaluate(scanned_data)  # Compute indicators
    │
    ├─► generator.generate_signal(evaluated_data)  # Generate signal
    │       │
    │       ├─► If BUY/SELL:
    │       │       └─► dispatcher.dispatch(signal)     # Execute trade
    │       │
    │       └─► Track signal in signals_received
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
Evaluation engine that computes technical indicators from raw market data using vnstock_ta library.

### Dependencies
- `pandas` (DataFrame operations)
- `numpy` (numerical computations)
- `vnstock_ta` (technical analysis functions) - optional, with fallback

### Class: `EvaluationEngine`

#### Responsibilities
1. Compute technical indicators on OHLCV data
2. Manage indicator cache
3. Provide fallback implementations when vnstock_ta unavailable
4. Return enriched DataFrame with all indicators

#### Indicator Computation Pipeline
```
Input:  OHLCV DataFrame
    │
    ├─► Try vnstock_ta (preferred)
    │   ├─► RSI (14 period)
    │   ├─► MACD (12, 26, 9)
    │   ├─► Bollinger Bands (20, 2)
    │   ├─► EMA (12, 26 periods)
    │   ├─► ATR (14 period)
    │   └─► SMA (20, 50 periods)
    │
    └─► Fallback: numpy implementations
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
When `vnstock_ta` is not installed:
1. Catches `ImportError`
2. Logs warning message
3. Uses numpy-based fallback implementations
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
    symbol: str                              # Stock symbol
    action: str                              # BUY, SELL, or HOLD
    confidence: float = 0.0                  # Signal strength (0-1)
    timestamp: datetime = field(default_factory=datetime.now)
    price: Optional[float] = None            # Execution price
    volume: Optional[int] = None             # Trade volume
    metadata: Dict[str, Any] = field(default_factory=dict)  # Context
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
      'strategies': ['rsi_macd'],              # Enabled strategies
      'thresholds': {                           # Strategy thresholds
          'rsi_overbought': 70,
          'rsi_oversold': 30,
          'macd_cross_threshold': 0.0
      },
      'cooldown_seconds': 60,                  # Min time between signals
      'min_confidence': 0.5                    # Minimum confidence to act
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
    success: bool                              # Success status
    status_code: Optional[int] = None          # HTTP status code
    response_data: Optional[Dict[str, Any]] = None  # Response body
    error_message: Optional[str] = None        # Error details
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
        # Otherwise retry
        time.sleep(self.retry_delay)
    except Exception:
        time.sleep(self.retry_delay)
```

**Configuration**:
- `max_retries`: Maximum attempts (default: 3)
- `retry_delay`: Seconds between retries (default: 1.0)
- `timeout`: Request timeout in seconds (default: 10)

#### Authentication
- Supports Bearer token authentication
- API key added as `Authorization: Bearer {api_key}` header
- Secret key can be used for signature generation (future)

#### Payload Structure
```python
{
      "action": signal.action,              # BUY, SELL, HOLD
      "symbol": signal.symbol,              # Stock symbol
      "timestamp": signal.timestamp.isoformat(),
      "confidence": signal.confidence,       # Signal strength
      "price": signal.price,                # Execution price
      "volume": signal.volume,              # Trade volume
      "metadata": signal.metadata           # Additional context
}
```

#### Execution Flow
```
dispatch(signal)
    │
    ├─► Check circuit breaker (if open, return failure)
    │
    ├─► Build payload
    │
    ├─► Try broker API:
    │       ├─► Retry up to max_retries times
    │       ├─► On success: reset failure_count, close circuit
    │       └─► On failure: increment failure_count
    │
    ├─► If API failed, try webhook:
    │       └─► Same retry logic
    │
    └─► Return DispatchResult
```

### Design Patterns Used
- **Circuit Breaker**: Prevents cascading failures
- **Retry Pattern**: Handles transient failures
- **Fallback Pattern**: Alternative execution path
- **Builder Pattern**: Payload construction

### Error Handling
- All exceptions are caught and logged
- Failure count tracks consecutive failures
- Circuit breaker opens automatically on threshold breach
- Returns descriptive error messages

### Extension Points
- Add signature-based authentication
- Implement request queuing
- Add message queue integration (RabbitMQ, Kafka)
- Support WebSocket connections for real-time updates

---

## 6. Module: `src.utils`

### Purpose
Helper functions for configuration loading and utility operations.

### Dependencies
- `yaml` (YAML parsing)
- `logging` (error reporting)

### Function: `load_config(config_path: str) -> Dict[str, Any]`

#### Responsibilities
1. Load YAML configuration file
2. Handle missing file gracefully
3. Log warnings/errors appropriately
4. Return parsed configuration dict

#### Implementation
```python
def load_config(config_path: str) -> Dict[str, Any]:
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded configuration from {config_path}")
        return config
    except FileNotFoundError:
        logger.warning(f"Config file not found: {config_path}")
        return {}
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        return {}
```

#### Error Handling
| Exception | Action | Return |
|-----------|--------|--------|
| `FileNotFoundError` | Log warning | `{}` (empty dict) |
| `yaml.YAMLError` | Log error | `{}` (empty dict) |
| Other exceptions | Log error | `{}` (empty dict) |

#### Security
- Uses `yaml.safe_load()` to prevent arbitrary code execution
- Does not execute Python objects from YAML

### Design Patterns Used
- **Fail-Fast**: Returns empty config rather than crashing
- **Defensive Programming**: Catches all exceptions

---

## 7. Module: `backtest`

### Purpose
Backtesting module that executes the trading pipeline on historical data to evaluate strategy performance.

### Dependencies
- `pandas` (DataFrame operations)
- `src.agent.TradingAgent` (pipeline execution)
- `vnstock` (market data access - production only)

### Class: `BacktestRunner`

#### Responsibilities
1. Fetch historical market data
2. Iterate through each bar/candle
3. Execute pipeline for each bar
4. Collect and report trading signals
5. Provide backtest summary statistics

#### Backtest Workflow
```
run(start_date, end_date)
    │
    ├─► _get_historical_data(start_date, end_date)
    │       └─► Returns OHLCV DataFrame
    │
    ├─► Check if data is empty
    │       └─► Return {"error": "No data"} if empty
    │
    ├─► For each bar in data:
    │       ├─► agent.run_pipeline(bar)
    │       └─► If signal in [BUY, SELL]:
    │               └─► Add to results list
    │
    └─► Return summary dict:
            {
                "symbol": ...,
                "start_date": ...,
                "end_date": ...,
                "total_bars": ...,
                "total_signals": ...,
                "signals": [...]
            }
```

#### Output Structure
```python
{
      "symbol": "VNM",                    # Trading symbol
      "start_date": "2024-01-01",         # Backtest start
      "end_date": "2024-12-31",           # Backtest end
      "total_bars": 1000,                 # Total data points
      "total_signals": 50,                # Total signals generated
      "signals": [                        # Signal details
          {
              "date": "2024-01-15",
              "action": "BUY",
              "price": 28.50,
              "confidence": 0.85
          },
          ...
      ]
}
```

#### Data Fetching (Production)
```python
# In production, replace with:
import vnstock as vs
df = vs.init(self.agent.symbol).quotes(start=start_date, end=end_date)
```

**Current Implementation**: Returns empty DataFrame (placeholder)

### Design Patterns Used
- **Iterator Pattern**: Processes data sequentially
- **Reporter Pattern**: Generates summary statistics
- **Adapter Pattern**: Abstracts data source behind interface

### Extension Points
- Integrate with vnstock for real market data
- Add performance metrics (Sharpe ratio, max drawdown)
- Implement walk-forward analysis
- Add Monte Carlo simulation support

---

## 8. Module: `config`

### Purpose
YAML configuration file for strategy parameters and execution settings.

### File: `config/strategies.yaml`

#### Structure
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
    api_key: ""
    secret_key: ""
    max_retries: 3
    retry_delay: 1.0
    timeout: 10
    circuit_breaker_threshold: 5

general:
    symbol: "VNM"
    log_level: "INFO"
    cooldown_seconds: 60
    min_confidence: 0.5
```

#### Configuration Sections

| Section | Purpose | Key Parameters |
|---------|---------|----------------|
| `strategies` | Trading strategy definitions | name, enabled, parameters |
| `execution` | Broker API configuration | url, api_key, retries |
| `general` | Global settings | symbol, log_level, cooldown |

#### Strategy Parameters

**RSI Parameters**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| `rsi_period` | 14 | RSI calculation period |
| `rsi_overbought` | 70 | Overbought threshold |
| `rsi_oversold` | 30 | Oversold threshold |

**MACD Parameters**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| `macd_fast` | 12 | Fast EMA period |
| `macd_slow` | 26 | Slow EMA period |
| `macd_signal` | 9 | Signal line period |

**Execution Parameters**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| `execution_url` | - | Broker API endpoint |
| `api_key` | - | Authentication key |
| `secret_key` | - | Secret key |
| `max_retries` | 3 | Retry attempts |
| `retry_delay` | 1.0 | Seconds between retries |
| `timeout` | 10 | Request timeout |
| `circuit_breaker_threshold` | 5 | Failures before open |

**General Parameters**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| `symbol` | "VNM" | Default stock symbol |
| `log_level` | "INFO" | Logging level |
| `cooldown_seconds` | 60 | Min time between signals |
| `min_confidence` | 0.5 | Minimum confidence to act |

### Design Patterns Used
- **Configuration File Pattern**: Externalized configuration
- **Convention over Configuration**: Sensible defaults
- **Separation of Concerns**: Config separate from code

---

## Module Dependency Graph

```
main.py
    │
    └─► src/agent.py (TradingAgent)
            │
            ├─► src/scanning.py (DataScanner)
            │       └─► pandas
            │
            ├─► src/evaluation.py (EvaluationEngine)
            │       ├─► pandas
            │       ├─► numpy
            │       └─► vnstock_ta (optional)
            │
            ├─► src/strategy.py (SignalGenerator, TradeSignal)
            │       ├─► pandas
            │       └─► dataclasses
            │
            └─► src/dispatcher.py (SignalDispatcher)
                    ├─► requests
                    └─► json
```

---

**End of Module Specifications**
