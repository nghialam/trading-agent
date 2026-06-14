"""
Tests for DataScanner
"""

import unittest
import pandas as pd
import numpy as np


class TestDataScanner(unittest.TestCase):
    def setUp(self):
        from src.scanning import DataScanner
        
        self.valid_data = pd.DataFrame({
              'open': [100.0, 102.0, 101.0, 103.0],
              'high': [105.0, 106.0, 104.0, 107.0],
              'low': [98.0, 100.0, 99.0, 101.0],
              'close': [103.0, 105.0, 102.0, 106.0],
              'volume': [1000, 1500, 1200, 1800]
          })
        
        self.scanner = DataScanner(symbol="TEST")

    def test_scan_valid_data(self):
        result = self.scanner.scan(self.valid_data)
        pd.testing.assert_frame_equal(result, self.valid_data)

    def test_scan_empty_data_raises_error(self):
        empty_data = pd.DataFrame()
        with self.assertRaises(ValueError):
            self.scanner.scan(empty_data)

    def test_scan_missing_columns_raises_error(self):
        incomplete_data = pd.DataFrame({
              'open': [100.0],
              'close': [105.0]
          })
        with self.assertRaises(ValueError):
            self.scanner.scan(incomplete_data)

    def test_scan_invalid_price_range_raises_error(self):
        invalid_data = pd.DataFrame({
              'open': [100.0],
              'high': [95.0],
              'low': [102.0],
              'close': [103.0],
              'volume': [1000]
          })
        with self.assertRaises(ValueError):
            self.scanner.scan(invalid_data)

    def test_scan_cache_updated(self):
        self.scanner.scan(self.valid_data)
        self.assertIsNotNone(self.scanner.data_cache)
        self.assertEqual(len(self.scanner.data_cache), len(self.valid_data))

    def test_get_latest_bar(self):
        self.scanner.scan(self.valid_data)
        last_bar = self.scanner.get_latest_bar()
        self.assertEqual(len(last_bar), 1)
        self.assertEqual(last_bar.iloc[0]['close'], 106.0)

    def test_clear_cache(self):
        self.scanner.scan(self.valid_data)
        self.assertIsNotNone(self.scanner.data_cache)
        self.scanner.clear_cache()
        self.assertIsNone(self.scanner.data_cache)


if __name__ == '__main__':
    unittest.main()
