# System Architecture Specification

## Autonomous Trading Agent - VnStock Ecosystem

**Version:** 1.0.0  
**Date:** 2026-06-14  
**Author:** Nghia Lam

---

## 1. Overview

This document describes the system architecture of an autonomous high-frequency trading agent built on the VnStock ecosystem, designed for the Vietnamese stock market (HOSE, HNX, UPCOM).

The system implements a **four-stage pipeline architecture**:

```
┌─────────────┐       ┌──────────────┐       ┌──────────────────┐       ┌──────────────┐
│  Market       │────▶   │  Evaluation    │────▶   │  Signal            │────▶   │  Dispatch      │
│  Scanning     │        │  Engine        │        │  Generation        │        │  Engine        │
└─────────────┘        └──────────────┘        └──────────────────┘        └──────────────┘
     vnstock              vnstock_ta            Strategy Logic          Broker API
```

## 2. High-Level Architecture

### 2.1 Component Diagram

```
                    ┌─────────────────────┐
                    │   TradingAgent      │
                    │   (Orchestrator)    │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌───────────┐     ┌───────────┐     ┌───────────┐
    │ Data      │     │ Evaluation│     │ Signal    │
    │ Scanner   │     │ Engine    │     │ Generator │
    └───────────┘     └───────────┘     └───────────┘
                              │
                      ┌───────────┐
                      │ Dispatcher│
                      └───────────┘
```

### 2.2 Data Flow

1. **Input**: Raw OHLCV (Open, High, Low, Close, Volume) data from market source
2. **Scan**: Validate and clean incoming data
3. **Evaluate**: Compute technical indicators (RSI, MACD, Bollinger Bands, etc.)
4. **Generate**: Apply strategy logic to produce trading signals (BUY/SELL/HOLD)
5. **Dispatch**: Execute trades via broker API or webhook

### 2.3 Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Data Source | vnstock | Vietnamese stock market data access |
| Technical Analysis | vnstock_ta | RSI, MACD, Bollinger Bands, ATR, EMA, SMA |
| Data Processing | pandas >= 2.0.0 | DataFrame operations |
| Numerical Computing | numpy >= 1.24.0 | Array computations |
| HTTP Client | requests >= 2.31.0 | API communication |
| Configuration | pyyaml >= 6.0.1 | YAML config parsing |
| Backtesting | backtrader >= 1.9.76 | Historical strategy testing |

## 3. Pipeline Stages

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

**Fallback**: If `vnstock_ta` is not installed, uses numpy-based fallback implementations.

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

## 4. Configuration System

### 4.1 Configuration File (`config/strategies.yaml`)

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

### 4.2 Configuration Loading

- Uses `yaml.safe_load()` for secure parsing
- Returns empty dict `{}` if file not found (graceful degradation)
- Logs warnings/errors appropriately

## 5. Backtesting Module

**Location**: `backtest/__init__.py`  
**Class**: `BacktestRunner`  

**Purpose**: Execute backtests using historical data and the trading agent  

**Workflow**:
1. Fetch historical data (via vnstock integration)
2. Iterate through each bar/candle
3. Run pipeline for each bar
4. Collect and return signal results

**Output Format**:
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

## 6. Entry Point

**File**: `main.py`  
**CLI Interface**: argparse-based  

**Command Line Arguments**:
| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--symbol` | str | "VNM" | Stock symbol to trade |
| `--mode` | str | "backtest" | Mode: backtest or live |
| `--start-date` | str | "2024-01-01" | Backtest start date |
| `--end-date` | str | "2024-12-31" | Backtest end date |
| `--log-level` | str | "INFO" | Logging level |

## 7. Error Handling Strategy

### 7.1 Pipeline Errors
- Exceptions in pipeline execution are caught and logged
- Returns `None` on failure (HOLD behavior)
- Uses `exc_info=True` for detailed error logging

### 7.2 Data Validation Errors
- Raises `ValueError` for invalid/empty data
- Missing columns are reported explicitly

### 7.3 Dispatch Failures
- Circuit breaker opens after threshold failures
- Falls back to alternative execution interface (webhook)
- Logs all failure attempts

## 8. Logging

**Level**: Configurable via CLI or config file  
**Output**: Both file and console  
**Format**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`  

**Log Directories**:
- `logs/` - Auto-created for log files
- Default log: `logs/trading_agent.log`

## 9. Dependencies

```
vnstock>=1.0.0          # Vietnamese stock market data
vnstock-ta>=1.0.0       # Technical analysis indicators
vnstock-pipeline>=1.0.0 # Pipeline utilities
pandas>=2.0.0           # Data manipulation
numpy>=1.24.0           # Numerical computing
pytest>=7.3.0           # Testing
backtrader>=1.9.76      # Backtesting framework
requests>=2.31.0        # HTTP client
aiohttp>=3.8.5          # Async HTTP
pyyaml>=6.0.1           # YAML parsing
python-dotenv>=1.0.0    # Environment variables
tabulate>=0.9.0         # Table formatting
```

## 10. Project Structure

```
trading-agent-vnstock/
├── config/
│    └── strategies.yaml      # Strategy configuration
├── src/
│    ├── __init__.py
│    ├── agent.py             # Main trading agent
│    ├── scanning.py          # Market data scanner
│    ├── evaluation.py        # Technical analysis engine
│    ├── strategy.py          # Signal generation
│    ├── dispatcher.py        # Execution interface
│    └── utils.py             # Helper functions
├── backtest/
│    ├── __init__.py          # Backtest runner
│    └── runner.py            # Backtest execution
├── tests/
│    ├── __init__.py
│    ├── test_agent.py
│    ├── test_scanning.py
│    ├── test_evaluation.py
│    ├── test_strategy.py
│    ├── test_dispatcher.py
│    └── test_runner.py
├── docs/                    # Documentation
│    ├── SYSTEM_ARCHITECTURE.md
│    ├── API_REFERENCE.md
│    └── MODULE_SPECIFICATIONS.md
├── logs/                    # Log files (auto-created)
├── data/                    # Data cache (auto-created)
├── main.py                  # Entry point
├── requirements.txt         # Dependencies
├── setup.sh                 # Setup script
└── README.md                # Project overview
```

## 11. Future Enhancements

- [ ] Real-time market data streaming
- [ ] Additional strategy implementations (Mean Reversion, Momentum, etc.)
- [ ] Machine learning model integration
- [ ] Portfolio management module
- [ ] Risk management controls
- [ ] Performance metrics dashboard
- [ ] Docker containerization
- [ ] CI/CD pipeline integration

---

**End of System Architecture Specification**
