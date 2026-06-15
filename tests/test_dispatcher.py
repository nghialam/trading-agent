"""
Tests for SignalDispatcher
"""

import unittest
from unittest.mock import Mock, patch
import pandas as pd


class TestSignalDispatcher(unittest.TestCase):
    def setUp(self):
        from src.strategy import TradeSignal
        
        self.signal = TradeSignal(
            symbol="TEST",
            action="BUY",
            confidence=0.85,
            price=105.5,
            volume=1000
         )

    @patch('requests.post')
    def test_dispatch_with_api_success(self, mock_post):
        from src.dispatcher import SignalDispatcher
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'order_id': '12345'}
        mock_post.return_value = mock_response
        
        dispatcher = SignalDispatcher(config={
             'execution_url': 'https://api.test.com/orders',
             'api_key': 'test_key',
             'max_retries': 1
         })
        
        result = dispatcher.dispatch(self.signal)
        
        self.assertTrue(result.success)
        self.assertEqual(result.status_code, 200)

    @patch('requests.post')
    def test_dispatch_with_api_failure(self, mock_post):
        from src.dispatcher import SignalDispatcher
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        dispatcher = SignalDispatcher(config={
             'execution_url': 'https://api.test.com/orders',
             'max_retries': 1
         })
        
        result = dispatcher.dispatch(self.signal)
        
           # API fails, then falls back to webhook (no config), returns error
        self.assertFalse(result.success)
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        dispatcher = SignalDispatcher(config={
             'execution_url': 'https://api.test.com/orders',
             'max_retries': 1,
             'circuit_breaker_threshold': 3
         })
        
        for _ in range(3):
            result = dispatcher.dispatch(self.signal)
        
        self.assertTrue(dispatcher.circuit_open)

    def test_dispatch_no_config(self):
        from src.dispatcher import SignalDispatcher
        
        dispatcher = SignalDispatcher()
        result = dispatcher.dispatch(self.signal)
        
        self.assertFalse(result.success)
        self.assertIn("No execution interface", result.error_message)


if __name__ == '__main__':
    unittest.main()
