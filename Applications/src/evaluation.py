"""
Evaluation Engine
Computes technical indicators using pandas-ta / technical_indicators
"""

import logging
from typing import Dict, Any, Optional

import pandas as pd
import numpy as np


logger = logging.getLogger(__name__)


class EvaluationEngine:
    """
    Computes technical indicators from raw market data
    Uses technical_indicators module for Vietnamese stock market analysis
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
            # Use the technical_indicators module (pandas-ta compatible)
            return self._compute_with_technical_indicators(df)
        except ImportError:
            logger.warning("technical_indicators not available. Using minimal indicators.")
            return self._compute_minimal_indicators(df)

    def _compute_with_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute indicators using technical_indicators module"""
        from src.technical_indicators import Indicators
        
        indicator = Indicators(df)
        
        # RSI (14 period)
        df['RSI'] = indicator.rsi(length=14)
        
        # MACD
        macd_df = indicator.macd(fastperiod=12, slowperiod=26, signalperiod=9)
        df['MACD'] = macd_df['MACD']
        df['MACD_Signal'] = macd_df['MACD_Signal']
        df['MACD_Hist'] = macd_df['MACD_Hist']
        
        # Bollinger Bands (20 period)
        bbands_df = indicator.bbands(length=20, std=2.0)
        df['BB_Upper'] = bbands_df['BB_UPPER']
        df['BB_Middle'] = bbands_df['BB_MIDDLE']
        df['BB_Lower'] = bbands_df['BB_LOWER']
        
        # EMA (12 and 26 periods)
        df['EMA_12'] = indicator.ema(period=12)
        df['EMA_26'] = indicator.ema(period=26)
        
        # ATR (14 period)
        df['ATR'] = indicator.atr(length=14)
        
        # SMA (20 and 50 periods)
        df['SMA_20'] = indicator.sma(length=20)
        df['SMA_50'] = indicator.sma(length=50)
        
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

    def _compute_minimal_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute minimal indicators using only pandas/numpy"""
        logger.info("Using minimal indicator calculation")
        
        # Simple RSI approximation
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
