#!/bin/bash
# Setup script for vnstock trading agent project

echo "Setting up VnStock Trading Agent..."
echo ""

# Create directories if they don't exist
mkdir -p src tests backtest config data logs

# Create __init__.py files where needed
touch src/__init__.py
touch tests/__init__.py
touch backtest/__init__.py

echo "✓ Directories created"

# Check if all files exist
if [ ! -f "src/agent.py" ]; then
    echo "✗ src/agent.py missing - please create manually"
else
    echo "✓ src/agent.py exists"
fi

if [ ! -f "config/strategies.yaml" ]; then
    echo "✗ config/strategies.yaml missing - please create manually"
else
    echo "✓ config/strategies.yaml exists"
fi

echo ""
echo "To install dependencies, run:"
echo "  pip install -r requirements.txt"
echo ""
echo "To run the trading agent:"
echo "  python main.py --symbol VNM --mode backtest"
echo ""
