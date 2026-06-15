"""
Market Data Scanning Layer
Responsible for ingesting and validating market data
"""

import logging
from typing import Optional
from datetime import datetime

import pandas as pd


logger = logging.getLogger(__name__)


class DataScanner:
    """
    Market Scanner that ingests raw market data
    Uses vnstock for Vietnamese market data access
    """

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.data_cache: Optional[pd.DataFrame] = None
        
        logger.info(f"DataScanner initialized for {symbol}")

    def scan(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """
        Scan and validate incoming market data
        
        Args:
            raw_data: Raw OHLCV DataFrame from data source
            
        Returns:
            Validated DataFrame ready for evaluation
            
        Raises:
            ValueError: If data is invalid or incomplete
        """
        if raw_data.empty:
            raise ValueError("Empty data received")
        
        # Required columns for trading
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        
        # Check if all required columns exist
        missing_cols = [col for col in required_columns if col not in raw_data.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Validate data types
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if not pd.api.types.is_numeric_dtype(raw_data[col]):
                raise ValueError(f"Column {col} must be numeric")
        
        # Validate price ranges (basic sanity check)
        if (raw_data['high'] < raw_data['low']).any():
            raise ValueError("Invalid OHLC data: High < Low detected")
        
        if (raw_data['close'] > raw_data['high']).any() or \
                (raw_data['close'] < raw_data['low']).any():
            raise ValueError("Close price outside High/Low range")
        
        # Cache last valid data
        self.data_cache = raw_data.copy()
        
        logger.debug(f"Scanned {len(raw_data)} rows for {self.symbol}")
        return raw_data

    def get_latest_bar(self) -> Optional[pd.DataFrame]:
        """
        Get the latest bar from cache
        
        Returns:
            Latest bar as DataFrame or None
        """
        if self.data_cache is None:
            return None
        
        return self.data_cache.tail(1)

    def clear_cache(self):
        """Clear cached data"""
        self.data_cache = None
        logger.debug("Data cache cleared")
