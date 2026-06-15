"""
Tests for SignalGenerator
"""

import unittest
import pandas as pd
from datetime import datetime


class TestSignalGenerator(unittest.TestCase):
    def setUp(self):
        from src.strategy import SignalGenerator
        
        n_rows = 60
        self.sample_data = pd.DataFrame({
            'open': [100.0 + i * 0.5 for i in range(n_rows)],
            'high': [102.0 + i * 0.5 for i in range(n_rows)],
            'low': [98.0 + i * 0.5 for i in range(n_rows)],
            'close': [101.0 + i * 0.5 for i in range(n_rows)],
            'volume': [1000 + i * 10 for i in range(n_rows)]
        })
        
        self.sample_data['RSI'] = 45.0 + (self.sample_data.index % 20) * 2
        self.sample_data['MACD'] = self.sample_data['close'] * 0.01
        self.sample_data['MACD_Signal'] = self.sample_data['close'] * 0.008
        self.sample_data['MACD_Hist'] = self.sample_data['MACD'] - self.sample_data['MACD_Signal']
        
        idx_buy = self.sample_data[(self.sample_data['RSI'] < 30) & 
                                   (self.sample_data['MACD_Hist'] > 0)].index[0] if \
                   len(self.sample_data[(self.sample_data['RSI'] < 30) & 
                                        (self.sample_data['MACD_Hist'] > 0)]) > 0 else 2
        
        idx_sell = self.sample_data[(self.sample_data['RSI'] > 70) & 
                                    (self.sample_data['MACD_Hist'] < 0)].index[0] if \
                   len(self.sample_data[(self.sample_data['RSI'] > 70) & 
                                        (self.sample_data['MACD_Hist'] < 0)]) > 0 else 5
        
        self.sample_data.loc[idx_buy, 'RSI'] = 25.0
        self.sample_data.loc[idx_buy, 'MACD_Hist'] = 1.0
        
        self.sample_data.loc[idx_sell, 'RSI'] = 75.0
        self.sample_data.loc[idx_sell, 'MACD_Hist'] = -1.0
        
        self.generator = SignalGenerator(
            symbol="TEST",
            config={
                'strategies': ['rsi_macd'],
                'thresholds': {
                    'rsi_overbought': 70,
                    'rsi_oversold': 30
                },
                'cooldown_seconds': 0,
                'min_confidence': 0.0
            }
        )

    def test_generate_signal_buy(self):
        test_row = pd.DataFrame([{
            'RSI': 25.0,
            'MACD_Hist': 1.0,
            'MACD': 1.0,
            'MACD_Signal': 0.8
        }])
        
        signal = self.generator.generate_signal(test_row)
        
        self.assertIsNotNone(signal)
        self.assertEqual(signal.action, 'BUY')

    def test_generate_signal_sell(self):
        test_row = pd.DataFrame([{
            'RSI': 75.0,
            'MACD_Hist': -1.0,
            'MACD': 0.8,
            'MACD_Signal': 1.0
        }])
        
        signal = self.generator.generate_signal(test_row)
        
        self.assertIsNotNone(signal)
        self.assertEqual(signal.action, 'SELL')

    def test_generate_signal_hold(self):
        test_row = pd.DataFrame([{
            'RSI': 50.0,
            'MACD_Hist': 0.1,
            'MACD': 0.5,
            'MACD_Signal': 0.6
        }])
        
        signal = self.generator.generate_signal(test_row)
        
        self.assertIsNotNone(signal)
        self.assertEqual(signal.action, 'HOLD')

    def test_generate_signal_empty_data(self):
        empty_data = pd.DataFrame()
        signal = self.generator.generate_signal(empty_data)
        self.assertIsNone(signal)


if __name__ == '__main__':
    unittest.main()
