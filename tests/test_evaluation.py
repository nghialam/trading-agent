"""
Tests for EvaluationEngine
"""

import unittest
import pandas as pd
import numpy as np


class TestEvaluationEngine(unittest.TestCase):
    def setUp(self):
        from src.evaluation import EvaluationEngine
        
        n_rows = 60
        self.test_data = pd.DataFrame({
               'open': np.random.randn(n_rows) * 10 + 100,
               'high': np.random.randn(n_rows) * 10 + 105,
               'low': np.random.randn(n_rows) * 10 + 95,
               'close': np.random.randn(n_rows) * 10 + 100,
               'volume': np.random.randint(1000, 5000, n_rows)
           })
        
        self.test_data['high'] = self.test_data[['high', 'close']].max(axis=1)
        self.test_data['low'] = self.test_data[['low', 'close']].min(axis=1)
        
        self.evaluator = EvaluationEngine(symbol="TEST")

    def test_evaluate_empty_data_raises_error(self):
        empty_data = pd.DataFrame()
        with self.assertRaises(ValueError):
            self.evaluator.evaluate(empty_data)

    def test_evaluate_returns_dataframe(self):
        result = self.evaluator.evaluate(self.test_data)
        self.assertIsInstance(result, pd.DataFrame)

    def test_evaluate_adds_indicators(self):
        result = self.evaluator.evaluate(self.test_data)
        
        expected_columns = ['RSI', 'MACD', 'EMA_12', 'SMA_20']
        for col in expected_columns:
            self.assertIn(col, result.columns, f"Column {col} not found")

    def test_indicators_not_null(self):
        result = self.evaluator.evaluate(self.test_data)
        
        for col in ['RSI', 'EMA_12', 'SMA_20']:
            non_null_count = result[col].notna().sum()
            self.assertGreater(non_null_count, 0, f"{col} has no valid values")

    def test_get_indicator(self):
        self.evaluator.evaluate(self.test_data)
        
        rsi_series = self.evaluator.get_indicator('RSI')
        
        self.assertIsNotNone(rsi_series)
        self.assertIsInstance(rsi_series, pd.Series)


if __name__ == '__main__':
    unittest.main()
