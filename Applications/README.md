# Autonomous Trading Agent - VnStock Ecosystem

An autonomous high-frequency trading agent built on the VnStock ecosystem, designed for the Vietnamese stock market (HOSE, HNX, UPCOM).

## Features
- Real-time market scanning with `vnstock` and `vnstock_pipeline`
- Technical analysis using `vnstock_ta` indicators
- Event-driven strategy engine
- Backtesting integration
- Configurable multi-strategy support

## Installation

### Prerequisites
- Python 3.9+
- pip or poetry for dependency management

### Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# For paid features (vnstock_ta, vnstock_pipeline)
pip install vnstock-data vnstock-news
```

## Project Structure
```
trading-agent-vnstock/
├── config/
│      └── strategies.yaml         # Strategy parameters and configurations
├── src/
│      ├── __init__.py
│      ├── agent.py                # Main trading agent class
│      ├── scanning.py             # Market data scanning layer
│      ├── evaluation.py           # Technical analysis & evaluation engine
│      ├── strategy.py             # Signal generation logic
│      ├── dispatcher.py           # Execution interface
│      └── utils.py                # Helper functions
├── tests/
│      ├── __init__.py
│      ├── test_agent.py
│      ├── test_scanning.py
│      ├── test_evaluation.py
│      ├── test_strategy.py
│      └── test_dispatcher.py
├── backtest/
│      ├── __init__.py
│      └── runner.py               # Backtesting execution
├── logs/                         # Auto-created for log files
├── data/                         # Cache for market data
├── main.py                       # Entry point
├── requirements.txt
└── README.md
```

## Usage

### Basic Example
```python
from src.agent import TradingAgent

# Initialize agent with strategy config
agent = TradingAgent(
    symbol='VNM',
    strategy_config='config/strategies.yaml'
)

# Run in backtest mode
results = agent.backtest(start_date='2024-01-01', end_date='2024-12-31')

# Run in live trading mode
agent.run_live()
```

### Strategy Configuration Example
See `config/strategies.yaml` for sample configurations.

## Testing
```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest -v tests/

# Run specific test file
pytest tests/test_strategy.py
```

## License
MIT License

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
