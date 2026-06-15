# Autonomous Trading Agent - Scalable 24/7 System

<div align="center">

An autonomous high-frequency trading agent built for the Vietnamese stock market (HOSE, HNX, UPCOM), featuring a multi-threaded scanner service, PostgreSQL database, and web-based management dashboard.

**Features:** 24/7 Automated Scanning • Real-time Signal Monitoring • Web Dashboard • REST API • Multi-Strategy Support

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-ff69b4.svg)](https://streamlit.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)

</div>

---

## 📋 Overview

This project implements a **scalable, 24/7 automated stock scanning and signal management system** consisting of three core components:

1. **Backend Scanner Service** — Multi-threaded service that continuously monitors the watchlist and generates trading signals
2. **Centralized Database** — PostgreSQL with normalized schema for storing signals, price data, and configuration
3. **Web-based Management Dashboard** — Streamlit UI for monitoring signals, managing watchlist, and viewing analytics

```
┌─────────────────────────────────────────────────────────────┐
│                      24/7 Automated Trading System              │
├─────────────────────────────────────────────────────────────┤
│                                                                 │
│     ┌──────────────┐       ┌──────────────┐       ┌──────────┐ │
│     │ Scanner        │────▶│ PostgreSQL      │────▶│ Streamlit  │ │
│     │ Service        │       │ Database        │       │ Dashboard  │ │
│     │ (FastAPI)      │       │                │       │            │ │
│     └──────────────┘       └──────────────┘       └──────────┘ │
│           │                          │                       │    │
│           ▼                          ▼                       │    │
│   vnstock API              Signal Storage                      │    │
│   Market Data              Watchlist Config                    │    │
└─────────────────────────────────────────────────────────────┘     │
```

## ✨ Features

- 🔄 **24/7 Automated Scanning** with multi-threaded ThreadPoolExecutor
- 📊 **Real-time Signal Monitoring** via REST API and web dashboard
- 🗄️ **PostgreSQL Database** with normalized schema for extensible metadata
- 🌐 **FastAPI Backend** with comprehensive REST endpoints
- 📱 **Streamlit Dashboard** for signal management and analytics
- 📈 **20+ Technical Indicators** (RSI, MACD, Bollinger Bands, ATR, etc.)
- ⚡ **Priority-based Updates** (VN30 stocks scanned more frequently)
- 🔒 **Automated Error Recovery** with retry logic and circuit breaker
- 📝 **Comprehensive Logging** for all scanner activities

## 🏗️ Project Structure

```
trading-agent/
├── config/
│     └── strategies.yaml              # Strategy parameters and configurations
├── database/
│     ├── __init__.py
│     ├── config.py                    # PostgreSQL connection & SQLAlchemy setup
│     └── models.py                    # ORM models (Watchlist, Signal, etc.)
├── services/
│     ├── __init__.py
│     └── scanner.py                   # Multi-threaded scanner service
├── src/
│     ├── __init__.py
│     ├── agent.py                     # Main trading agent class
│     ├── scanning.py                  # Data validation
│     ├── evaluation.py                # Technical analysis engine
│     ├── strategy.py                  # Signal generation logic
│     ├── dispatcher.py                # Execution interface
│     ├── technical_indicators.py      # 20+ indicators (numpy/pandas)
│     └── utils.py                     # Helper functions
├── backtest/
│     ├── __init__.py
│     └── runner.py                    # Backtesting execution
├── api/
│     ├── __init__.py
│     ├── main.py                      # FastAPI application entry point
│     └── routes/
│         ├── __init__.py
│         ├── signals.py               # Signal CRUD endpoints
│         ├── watchlist.py             # Watchlist management endpoints
│         └── scanner.py               # Scanner control endpoints
├── dashboard/
│     ├── __init__.py
│     └── app.py                       # Streamlit web dashboard
├── tests/
│     ├── __init__.py
│     ├── test_agent.py
│     ├── test_scanning.py
│     ├── test_evaluation.py
│     ├── test_strategy.py
│     ├── test_dispatcher.py
│     └── test_runner.py
├── logs/                              # Auto-created for log files
├── data/                              # Cache for market data
├── main.py                            # CLI entry point
├── requirements.txt                   # Python dependencies
├── Dockerfile                         # Container setup
├── docker-compose.yml                 # Multi-service orchestration
└── README.md                          # This file
```

## 🚀 Installation

### Prerequisites

- Python 3.9 or higher
- PostgreSQL 14+ (with `psycopg2` driver)
- pip or poetry for dependency management
- Access to Vietnamese stock market data (via vnstock)

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/nghialam/trading-agent.git
cd trading-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate              # macOS/Linux
venv\Scripts\activate                 # Windows

# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL database
export DATABASE_URL="postgresql://trading_user:trading_pass@localhost:5432/trading_agent"

# Initialize database schema
python -c "from database.config import init_db; init_db()"
```

## 📖 Usage

### 1. Command Line Interface (CLI)

```bash
# Run backtest for VNM stock
python main.py --symbol VNM --mode backtest

# Run with custom date range
python main.py --symbol FPT --mode backtest \
        --start-date 2024-01-01 --end-date 2024-12-31

# Set logging level
python main.py --symbol VNM --mode live --log-level DEBUG
```

### 2. Run Scanner Service (24/7)

```bash
# Start the scanner service in background
python -c "from services.scanner import get_scanner; get_scanner().run()"

# Or use systemd for production deployment
sudo systemctl start trading-scanner
sudo systemctl status trading-scanner
```

### 3. Start FastAPI Backend

```bash
# Run API server on port 8000
uvicorn api.main:app --reload --port 8000

# Production mode with multiple workers
uvicorn api.main:app --workers 4 --host 0.0.0.0 --port 8000
```

### 4. Launch Streamlit Dashboard

```bash
# Start dashboard on port 8501
streamlit run dashboard/app.py --server.port 8501

# Access at http://localhost:8501
```

## 🗄️ Database Schema

### Core Tables

| Table | Description | Key Columns |
|-------|-------------|-------------|
| `Watchlist` | Active stocks to monitor | symbol, name, sector, priority, enabled |
| `Signal` | Generated trading signals | symbol, timestamp, signal_type, confidence_score, indicators (JSON) |
| `PriceData` | Historical OHLCV data | symbol, timestamp, open, high, low, close, volume |
| `SystemLog` | Activity logging | timestamp, level, component, message, details |
| `ScannerConfig` | Runtime configuration | key, value (key-value store) |

### Indexes

- `idx_signal_symbol_time`: Composite index on Signal(symbol, timestamp)
- `idx_signal_confidence`: Filter by confidence score
- `idx_signal_type`: Filter by signal type (BUY/SELL/HOLD)
- `idx_price_data_symbol_time`: Composite index on PriceData(symbol, timestamp)

## 📡 REST API Endpoints

### Signals

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/signals` | List all signals (with filters) |
| GET | `/api/signals/{id}` | Get signal details |
| POST | `/api/signals` | Create new signal (manual) |
| DELETE | `/api/signals/{id}` | Delete signal |

### Watchlist

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/watchlist` | List all watchlist stocks |
| POST | `/api/watchlist` | Add stock to watchlist |
| PUT | `/api/watchlist/{id}` | Update stock config |
| DELETE | `/api/watchlist/{id}` | Remove from watchlist |

### Scanner

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/scanner/status` | Get scanner status |
| POST | `/api/scanner/start` | Start scanning |
| POST | `/api/scanner/stop` | Stop scanning |
| POST | `/api/scanner/scan/{symbol}` | Scan single stock |

## ⚙️ Configuration

### Strategy Config (`config/strategies.yaml`)

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
    api_key: ""                # Set your API key
    secret_key: ""             # Set your secret key
    max_retries: 3
    retry_delay: 1.0
    timeout: 10
    circuit_breaker_threshold: 5

scanner:
    scan_interval: 30            # Default scan interval (seconds)
    high_priority_interval: 10   # VN30 stocks
    low_priority_interval: 60    # Other stocks
    max_workers: 10              # Thread pool size
```

### Environment Variables

```bash
# Database connection
export DATABASE_URL="postgresql://user:pass@localhost:5432/trading_agent"

# vnstock API credentials (if required)
export VNSTOCK_API_KEY="your_api_key"

# Logging level
export LOG_LEVEL="INFO"
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

## 🐳 Docker Deployment

```bash
# Build and run all services
docker-compose up --build

# Run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 📊 Pipeline Architecture

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│ vnstock API     │────▶│ Scanner        │────▶│ PostgreSQL      │────▶│ Streamlit      │
│ Market Data     │       │ Service        │       │ Database        │       │ Dashboard      │
└──────────────┘       └──────────────┘       └──────────────┘       └──────────────┘
                          │
                          ▼
                   FastAPI REST API
                   Signal CRUD
                   Watchlist Mgmt
```

## 📚 Documentation

- [System Architecture](docs/SYSTEM_ARCHITECTURE.md) — System overview, component diagrams, technology stack
- [API Reference](docs/API_REFERENCE.md) — Complete API reference for all classes and methods
- [Module Specifications](docs/MODULE_SPECIFICATIONS.md) — Detailed module specs with design patterns

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
