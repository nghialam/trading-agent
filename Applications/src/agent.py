"""
Main Trading Agent Class
Coordinates all pipeline stages
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from src.scanning import DataScanner
from src.evaluation import EvaluationEngine
from src.strategy import SignalGenerator, TradeSignal
from src.dispatcher import SignalDispatcher
from src.utils import load_config


logger = logging.getLogger(__name__)


class TradingAgent:
    """
    Main Trading Agent that orchestrates the four-stage pipeline:
      1. Market Scanning
      2. Evaluation
      3. Signal Generation
      4. Signal Dispatch
    """

    def __init__(self, symbol: str = "VNM", strategy_config: Optional[str] = None):
        self.symbol = symbol
        
        # Load configuration if provided
        config = {}
        if strategy_config:
            config = load_config(strategy_config)
        
        # Initialize pipeline components
        self.scanner = DataScanner(symbol=symbol)
        self.evaluator = EvaluationEngine(symbol=symbol)
        self.generator = SignalGenerator(
            symbol=symbol,
            config=config.get('strategies', {})
        )
        self.dispatcher = SignalDispatcher(config=config.get('execution', {}))
        
        # Trading state
        self.is_running = False
        self.signals_received: list = []
        self.trades_executed: list = []
        
        logger.info(f"TradingAgent initialized for {symbol}")

    def run_pipeline(self, bar_data: pd.DataFrame) -> Optional[TradeSignal]:
        """
        Execute the full pipeline for a single bar of data
        
        Args:
            bar_data: DataFrame with OHLCV data
            
        Returns:
            TradeSignal if action is BUY or SELL, else None (HOLD)
        """
        try:
            # Step 1: Scan/Validate Data
            scanned_data = self.scanner.scan(bar_data)
            
            # Step 2: Evaluate Technical Indicators
            evaluated_data = self.evaluator.evaluate(scanned_data)
            
            # Step 3: Generate Signal
            signal = self.generator.generate_signal(evaluated_data)
            
            if signal and signal.action in ["BUY", "SELL"]:
                # Step 4: Dispatch Signal
                dispatch_result = self.dispatcher.dispatch(signal)
                
                logger.info(
                    f"Signal Generated: {signal.action} {self.symbol} "
                    f"(Confidence: {signal.confidence:.2%})"
                )
                
                # Track signals
                self.signals_received.append({
                    'signal': signal,
                    'dispatch_result': dispatch_result
                })
                
                return signal
            
            elif signal and signal.action == "HOLD":
                logger.debug(f"HOLD signal for {self.symbol}")
            
            return None
        
        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}", exc_info=True)
            return None

    def backtest(
        self, 
        start_date: str = "2024-01-01", 
        end_date: str = "2024-12-31"
    ) -> Dict[str, Any]:
        """
        Run backtesting on historical data
        
        Args:
            start_date: Start date for backtest
            end_date: End date for backtest
            
        Returns:
            Dictionary with backtest results
        """
        logger.info(
            f"Starting backtest for {self.symbol} "
            f"from {start_date} to {end_date}"
        )
        
        # Get historical data (in production, use vnstock)
        historical_data = self._fetch_historical_data(start_date, end_date)
        
        if historical_data.empty:
            logger.warning("No historical data available")
            return {"error": "No data available"}
        
        trades_log = []
        
        # Process each bar
        for date in historical_data.index:
            bar = historical_data.loc[date]
            
            signal = self.run_pipeline(bar.to_frame().T)
            
            if signal and signal.action in ["BUY", "SELL"]:
                trade = {
                    'date': str(date),
                    'symbol': signal.symbol,
                    'action': signal.action,
                    'price': signal.price,
                    'confidence': signal.confidence
                }
                trades_log.append(trade)
        
        results = {
            'symbol': self.symbol,
            'start_date': start_date,
            'end_date': end_date,
            'total_trades': len(trades_log),
            'trades': trades_log
        }
        
        logger.info(f"Backtest completed: {results['total_trades']} trades")
        return results

    def run_live(self):
        """
        Run in live trading mode
        (In production, this would connect to real-time data feeds)
        """
        logger.info(f"Starting live trading for {self.symbol}")
        self.is_running = True
        
        try:
            # This is a placeholder - in production:
            # 1. Connect to vnstock_pipeline for real-time data
            # 2. Process each incoming bar/tick
            # 3. Dispatch signals to broker
            
            logger.info("Live trading mode started (placeholder)")
            
        except KeyboardInterrupt:
            logger.info("Live trading stopped by user")
            self.is_running = False
        finally:
            self.cleanup()

    def _fetch_historical_data(
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
        # df = vs.init(self.symbol).quotes(start=start_date, end=end_date)
        
        # Generate synthetic OHLCV data for testing
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        n = len(dates)
        if n == 0:
            return pd.DataFrame()
        
        import numpy as np
        np.random.seed(42)
        base_price = 100.0
        returns = np.random.randn(n) * 0.5
        closes = [base_price] + list(np.cumsum(returns) + base_price)
        closes = closes[1:]  # align with n
        opens = closes[:-1] + [base_price]
        highs = [max(o, c) + abs(r) for o, c, r in zip(opens, closes, returns)]
        lows = [min(o, c) - abs(r) for o, c, r in zip(opens, closes, returns)]
        volumes = [max(100, int(abs(r) * 2000 + 500)) for r in returns]
        
        df = pd.DataFrame({
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        }, index=dates)
        
        return df

    def cleanup(self):
        """Clean up resources"""
        self.is_running = False
        logger.info(f"Cleanup completed for {self.symbol}")
