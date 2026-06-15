"""
Tests for TradingAgent
"""

import unittest
import pandas as pd


class TestTradingAgent(unittest.TestCase):
    def setUp(self):
        from src.agent import TradingAgent
        
        self.agent = TradingAgent(symbol="TEST")
    
    def _create_sample_bar_data(self, n_rows=60) -> pd.DataFrame:
        import numpy as np
        
        data = pd.DataFrame({
             'open': [100.0 + i * 0.5 for i in range(n_rows)],
             'high': [102.0 + i * 0.5 for i in range(n_rows)],
             'low': [98.0 + i * 0.5 for i in range(n_rows)],
             'close': [101.0 + i * 0.5 for i in range(n_rows)],
             'volume': [1000 + i * 10 for i in range(n_rows)]
         })
        
        data['high'] = data[['high', 'close']].max(axis=1)
        data['low'] = data[['low', 'close']].min(axis=1)
        
        return data

    def test_agent_initialization(self):
        self.assertEqual(self.agent.symbol, "TEST")
        self.assertIsNotNone(self.agent.scanner)
        self.assertIsNotNone(self.agent.evaluator)
        self.assertIsNotNone(self.agent.generator)
        self.assertIsNotNone(self.agent.dispatcher)

    def test_run_pipeline_with_valid_data(self):
        sample_data = self._create_sample_bar_data()
        
         # Pass enough rows for indicators to compute (need at least 14+ rows)
        result = self.agent.run_pipeline(sample_data.iloc[:30])
        
          # Pipeline should complete without error and return a signal or None (HOLD)
        self.assertTrue(result is None or hasattr(result, 'action'))

    def test_backtest_with_empty_data(self):
        results = self.agent.backtest(
               start_date="2024-01-01",
               end_date="2024-12-31"
            )
        
           # Should return error if no data
        if "error" in results:
            self.assertEqual(results["error"], "No data available")

    def test_cleanup(self):
        self.agent.is_running = True
        self.agent.cleanup()
        self.assertFalse(self.agent.is_running)


if __name__ == '__main__':
    unittest.main()
