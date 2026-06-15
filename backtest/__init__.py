"""
Backtest Runner Module
Executes backtesting with VnStock data integration
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

import pandas as pd


logger = logging.getLogger(__name__)


class BacktestRunner:
    """
    Runs backtests using historical data and the trading agent
    Can integrate with vnstock for real market data
    """

    def __init__(self, agent):
        self.agent = agent
        self.results: list = []

        logger.info("BacktestRunner initialized")

    def run(
        self,
        start_date: str = "2024-01-01",
        end_date: str = "2024-12-31"
    ) -> Dict[str, Any]:
        """
        Run backtest on historical data

        Args:
            start_date: Start date for backtest
            end_date: End date for backtest

        Returns:
            Dictionary with backtest results
        """
        logger.info(
            f"Starting backtest: {self.agent.symbol} "
            f"from {start_date} to {end_date}"
        )

        # Get historical data
        data = self._get_historical_data(start_date, end_date)

        if data.empty:
            logger.warning("No data available for backtest")
            return {"error": "No data"}

        results = []

        # Process each bar
        for index in data.index:
            bar = data.loc[index]

            try:
                signal = self.agent.run_pipeline(bar.to_frame().T)

                if signal and signal.action in ["BUY", "SELL"]:
                    results.append({
                        "date": str(index),
                        "action": signal.action,
                        "price": signal.price,
                        "confidence": signal.confidence
                    })
            except Exception as e:
                logger.error(f"Error processing bar {index}: {str(e)}")

        output = {
            "symbol": self.agent.symbol,
            "start_date": start_date,
            "end_date": end_date,
            "total_bars": len(data),
            "total_signals": len(results),
            "signals": results
        }

        logger.info(f"Backtest completed: {len(results)} signals generated")
        return output

    def _get_historical_data(
        self,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        Fetch historical data (placeholder - use vnstock in production)

        Returns:
            DataFrame with OHLCV data
        """
        # In production, replace with:
        # import vnstock as vs
        # df = vs.init(self.agent.symbol).quotes(start=start_date, end=end_date)

        # Placeholder for now
        return pd.DataFrame()
