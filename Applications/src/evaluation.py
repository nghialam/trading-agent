"""
Evaluation Engine
Computes technical indicators using vnstock_ta
"""

import logging
from typing import Dict, Any, Optional

import pandas as pd
import numpy as np


logger = logging.getLogger(__name__)


class EvaluationEngine:
    """
    Computes technical indicators from raw market data
    Uses vnstock_ta for Vietnamese stock market analysis
    """

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.indicators: Dict[str, pd.Series] = {}
        
        logger.info(f"EvaluationEngine initialized for {symbol}")

    def evaluate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all technical indicators on the input data
        
        Args:
            data: DataFrame with OHLCV columns
            
        Returns:
            DataFrame with added indicator columns
        """
        if data.empty:
            raise ValueError("Empty data passed to evaluator")
        
        result = data.copy()
        
        # Compute all indicators
        result = self._compute_indicators(result)
        
        logger.debug(f"Computed indicators for {self.symbol}")
        return result

    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute technical indicators
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with added indicators
        """
        try:
            # Try to use vnstock_ta if available
            return self._compute_with_vnstock_ta(df)
        except ImportError:
            logger.warning("vnstock_ta not installed. Using fallback indicators.")
            return self._compute_fallback_indicators(df)

    def _compute_with_vnstock_ta(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute indicators using vnstock_ta"""
        from vnstock_ta import RSI as ta_rsi
        from vnstock_ta import MACD as ta_macd
        
        # RSI (14 period)
        df['RSI'] = ta_rsi(df['close'], timeperiod=14)
        
        # MACD
        macd_line, signal_line, histogram = ta_macd(
            df['close'], 
            fastperiod=12, 
            slowperiod=26, 
            signalperiod=9
        )
        df['MACD'] = macd_line
        df['MACD_Signal'] = signal_line
        df['MACD_Hist'] = histogram
        
        # Bollinger Bands (20 period)
        from vnstock_ta import BBANDS as ta_bbands
        upper, middle, lower = ta_bbands(
            df['close'], 
            timeperiod=20, 
            nbdevup=2, 
            nbdevdn=2, 
            matype=0
        )
        df['BB_Upper'] = upper
        df['BB_Middle'] = middle
        df['BB_Lower'] = lower
        
        # EMA (12 and 26 periods)
        from vnstock_ta import EMA as ta_ema
        df['EMA_12'] = ta_ema(df['close'], timeperiod=12)
        df['EMA_26'] = ta_ema(df['close'], timeperiod=26)
        
        # ATR (14 period)
        from vnstock_ta import ATR as ta_atr
        df['ATR'] = ta_atr(df['high'], df['low'], df['close'], timeperiod=14)
        
        # SMA (20 and 50 periods)
        from vnstock_ta import SMA as ta_sma
        df['SMA_20'] = ta_sma(df['close'], timeperiod=20)
        df['SMA_50'] = ta_sma(df['close'], timeperiod=50)
        
        self.indicators = {
            'RSI': df['RSI'],
            'MACD': df['MACD'],
            'MACD_Signal': df['MACD_Signal'],
            'MACD_Hist': df['MACD_Hist'],
            'BB_Upper': df['BB_Upper'],
            'BB_Middle': df['BB_Middle'],
            'BB_Lower': df['BB_Lower'],
            'EMA_12': df['EMA_12'],
            'EMA_26': df['EMA_26'],
            'ATR': df['ATR'],
            'SMA_20': df['SMA_20'],
            'SMA_50': df['SMA_50']
        }
        
        return df

    def _compute_fallback_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute fallback indicators using pandas/numpy if vnstock_ta is not available"""
        logger.info("Using fallback indicator calculation")
        
        # Simple RSI approximation using rolling statistics (avoid division by zero)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, np.finfo(float).eps)
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Simple EMA
        df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()
        
        # SMA
        df['SMA_20'] = df['close'].rolling(window=20).mean()
        df['SMA_50'] = df['close'].rolling(window=50).mean()
        
        # Placeholder for other indicators
        df['MACD'] = 0.0
        df['MACD_Signal'] = 0.0
        df['MACD_Hist'] = 0.0
        df['BB_Upper'] = df['close'] * 1.02
        df['BB_Middle'] = df['close']
        df['BB_Lower'] = df['close'] * 0.98
        df['ATR'] = df['high'] - df['low']
        
        # Update indicators dict for fallback
        self.indicators = {
            'RSI': df['RSI'],
            'MACD': df['MACD'],
            'EMA_12': df['EMA_12'],
            'EMA_26': df['EMA_26'],
            'SMA_20': df['SMA_20'],
            'SMA_50': df['SMA_50']
        }
        
        return df

    def get_indicator(self, name: str) -> Optional[pd.Series]:
        """
        Get a specific indicator by name
        
        Args:
            name: Indicator name
            
        Returns:
            Series with indicator data or None
        """
        return self.indicators.get(name)
