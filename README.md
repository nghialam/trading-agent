# Autonomous Trading Agent - VnStock Ecosystem

<div align="center">

An autonomous high-frequency trading agent built on the VnStock ecosystem, designed for the Vietnamese stock market (HOSE, HNX, UPCOM).

**Features:** Real-time scanning • Technical Analysis • Strategy Engine • Backtesting • Multi-Strategy Support

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![vnstock](https://img.shields.io/badge/vnstock-1.0.0+-orange.svg)](https://github.com/vnstock/vnstock)

</div>

---

## 📋 Overview

This project implements an autonomous trading agent that leverages the VnStock ecosystem to analyze and trade Vietnamese stocks. The agent follows a four-stage pipeline:

1. **Market Scanning** - Ingest raw market data using `vnstock`
2. **Evaluation** - Compute technical indicators with `vnstock_ta`
3. **Signal Generation** - Apply strategy logic to generate trading signals
4. **Signal Dispatch** - Execute trades via configured broker API

## ✨ Features

- 📊 **Real-time Market Scanning** with `vnstock` and `vnstock_pipeline`
- 📈 **Technical Analysis** using `vnstock_ta` indicators (RSI, MACD, Bollinger Bands, etc.)
- ⚡ **Event-driven Strategy Engine** for high-frequency trading
- 🔍 **Backtesting Integration** with configurable parameters
- 🎛️ **Configurable Multi-Strategy Support** via YAML configuration
- 🔄 **Circuit Breaker Pattern** for robust execution

## 🏗️ Project Structure

```
trading-agent-vnstock/
├── config/
│     └── strategies.yaml            # Strategy parameters and configurations
├── src/
│     ├── __init__.py
│     ├── agent.py                   # Main trading agent class
│     ├── scanning.py                # Market data scanning layer
│     ├── evaluation.py              # Technical analysis & evaluation engine
│     ├── strategy.py                # Signal generation logic
│     ├── dispatcher.py              # Execution interface
│     └── utils.py                   # Helper functions
├── backtest/
│     ├── __init__.py
│     └── runner.py                  # Backtesting execution
├── tests/
│     ├── __init__.py
│     ├── test_agent.py
│     ├── test_scanning.py
│     ├── test_evaluation.py
│     ├── test_strategy.py
│     ├── test_dispatcher.py
│     └── test_runner.py
├── logs/                          # Auto-created for log files
├── data/                          # Cache for market data
├── main.py                        # Entry point
├── requirements.txt
└── README.md
```

## 🚀 Installation

### Prerequisites

- Python 3.9 or higher
- pip or poetry for dependency management
- Access to Vietnamese stock market data (via vnstock)

### Setup

```bash
# Clone the repository
git clone https://github.com/nghialam/trading-agent.git
cd trading-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate          # macOS/Linux
venv\Scripts\activate             # Windows

# Install dependencies
pip install -r requirements.txt

# For paid features (vnstock_ta, vnstock_pipeline)
pip install vnstock-data vnstock-news
```

## 📖 Usage

### Command Line Interface

```bash
# Run backtest for VNM stock
python main.py --symbol VNM --mode backtest

# Run with custom date range
python main.py --symbol FPT --mode backtest \
      --start-date 2024-01-01 --end-date 2024-12-31

# Set logging level
python main.py --symbol VNM --mode live --log-level DEBUG

# Run in live trading mode
python main.py --symbol VNM --mode live
```

### Programmatic Usage

```python
from src.agent import TradingAgent

# Initialize agent with strategy config
agent = TradingAgent(
    symbol='VNM',
    strategy_config='config/strategies.yaml'
)

# Run in backtest mode
results = agent.backtest(
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# Run in live trading mode
agent.run_live()
```

## ⚙️ Configuration

The `config/strategies.yaml` file contains all strategy parameters:

```yaml
strategies:
    # Available strategies
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
    # Execution API configuration
    execution_url: "https://api.broker.com/v1/orders"
    api_key: ""             # Set your API key
    secret_key: ""          # Set your secret key
    
    # Retry settings
    max_retries: 3
    retry_delay: 1.0
    timeout: 10
    
    # Circuit breaker
    circuit_breaker_threshold: 5

general:
    # General settings
    symbol: "VNM"           # Default symbol
    log_level: "INFO"
    
    # Cooldown between signals (seconds)
    cooldown_seconds: 60
    
    # Minimum confidence to act on signal
    min_confidence: 0.5
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest -v tests/

# Run specific test file
pytest tests/test_strategy.py

# Run with coverage report
pytest --cov=src tests/
```

## 📊 Pipeline Architecture

```
┌─────────────┐       ┌──────────────┐       ┌──────────────────┐       ┌──────────────┐
│  Market      │────▶  │  Evaluation   │────▶  │  Signal           │────▶  │  Dispatch     │
│  Scanning    │       │  Engine       │       │  Generation       │       │  Engine       │
└─────────────┘       └──────────────┘       └──────────────────┘       └──────────────┘
    vnstock              vnstock_ta            Strategy Logic          Broker API
```

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

### Contribution Guidelines

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📬 Contact

For questions or feedback, please open an issue on GitHub.

---

<div align="center">

**Built with ❤️ for the Vietnamese stock market**

[Report Bug](https://github.com/nghialam/trading-agent/issues) · [Request Feature](https://github.com/nghialam/trading-agent/issues)

</div>
