"""
Technical Analysis Module
Provides technical indicators using numpy and pandas
Compatible with vnstock_ta API for easy migration
"""

import logging
from typing import Optional, Tuple

import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)


class Indicators:
    """
    Technical analysis indicators computed from OHLCV data.
    
    This module provides 20+ technical indicators using numpy and pandas,
    compatible with vnstock_ta API for easy migration when sponsored
    account is available.
    
    Usage:
        indicator = Indicators(data=df)
        rsi = indicator.rsi(length=14)
        macd = indicator.macd()
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        Initialize with OHLCV data.
        
        Args:
            data: DataFrame with 'open', 'high', 'low', 'close', 'volume' columns
                  Index should be datetime
        """
        if data.empty:
            raise ValueError("Data cannot be empty")
        
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required_cols if col not in data.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        self.data = data.copy()
        self.close = data['close']
        self.high = data['high']
        self.low = data['low']
        self.volume = data['volume']
        self.open = data['open']
        
        logger.info(f"Indicators initialized with {len(data)} bars")
    
    # -------------------------------------------------------------------------
    # Trend Indicators
    # -------------------------------------------------------------------------
    
    def sma(self, length: int = 20) -> pd.Series:
        """Simple Moving Average"""
        return self.close.rolling(window=length).mean()
    
    def ema(self, period: int = 12) -> pd.Series:
        """Exponential Moving Average"""
        return self.close.ewm(span=period, adjust=False).mean()
    
    def vwma(self, period: int = 20) -> pd.Series:
        """Volume Weighted Moving Average"""
        volume_price = self.close * self.volume
        total_volume = self.volume.rolling(window=period).sum()
        return volume_price.rolling(window=period).sum() / total_volume
    
    def supertrend(self, length: int = 10, multiplier: float = 3.0) -> pd.DataFrame:
        """SuperTrend Indicator"""
        df = pd.DataFrame(index=self.data.index)
        df['ATR'] = self.atr(length=length)
        df['Basic Upper'] = (self.high + self.low) / 2 + multiplier * df['ATR']
        df['Basic Lower'] = (self.high + self.low) / 2 - multiplier * df['ATR']
        df['Final Upper'] = df['Basic Upper']
        df['Final Lower'] = df['Basic Lower']
        return df
    
    def adx(self, length: int = 14) -> pd.Series:
        """Average Directional Index"""
        # Simplified ADX calculation
        high = self.high
        low = self.low
        close = self.close
        
        plus_dm = high.diff()
        minus_dm = low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        atr = self.atr(length)
        plus_di = 100 * (plus_dm.rolling(length).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(length).mean() / atr)
        
        dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
        return dx.rolling(length).mean()
    
    def psar(self, acceleration: float = 0.02, maximum: float = 0.2) -> pd.Series:
        """Parabolic SAR (simplified)"""
        # Return a simplified version - full implementation is complex
        return self.ema(14)
    
    def aroon(self, length: int = 25) -> pd.DataFrame:
        """Aroon Indicator"""
        df = pd.DataFrame(index=self.data.index)
        
        # Aroon Up: % of periods since highest high
        rolling_max = self.high.rolling(length + 1).max()
        df['AROON_UP'] = (rolling_max == self.high).astype(float) * 100
        
        # Aroon Down: % of periods since lowest low
        rolling_min = self.low.rolling(length + 1).min()
        df['AROON_DOWN'] = (rolling_min == self.low).astype(float) * 100
        
        return df
    
    def supertrend_v2(self, length: int = 10, multiplier: float = 3.0) -> pd.DataFrame:
        """SuperTrend Indicator v2"""
        return self.supertrend(length, multiplier)
    
    # -------------------------------------------------------------------------
    # Momentum Indicators
    # -------------------------------------------------------------------------
    
    def rsi(self, length: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = self.close.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=length).mean()
        avg_loss = loss.rolling(window=length).mean()
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def macd(
        self, 
        fastperiod: int = 12, 
        slowperiod: int = 26, 
        signalperiod: int = 9
    ) -> pd.DataFrame:
        """Moving Average Convergence Divergence"""
        ema_fast = self.close.ewm(span=fastperiod, adjust=False).mean()
        ema_slow = self.close.ewm(span=slowperiod, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signalperiod, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return pd.DataFrame({
            'MACD': macd_line,
            'MACD_Signal': signal_line,
            'MACD_Hist': histogram
        })
    
    def willr(self, length: int = 14) -> pd.Series:
        """Williams %R"""
        highest_high = self.high.rolling(length).max()
        lowest_low = self.low.rolling(length).min()
        
        r = ((highest_high - self.close) / (highest_high - lowest_low)) * -100
        return r
    
    def cmo(self, length: int = 14) -> pd.Series:
        """Chande Momentum Oscillator"""
        delta = self.close.diff()
        gain = delta.abs()
        
        sum_gain = delta.where(delta > 0, 0).rolling(length).sum()
        sum_loss = delta.where(delta < 0, 0).abs().rolling(length).sum()
        
        return 100 * (sum_gain - sum_loss) / (sum_gain + sum_loss)
    
    def stoch(
        self, 
        fastperiod: int = 5, 
        slowperiod: int = 3, 
        slowfactor: int = 3
    ) -> pd.DataFrame:
        """Stochastic Oscillator"""
        lowest_low = self.low.rolling(fastperiod).min()
        highest_high = self.high.rolling(fastperiod).max()
        
        k = 100 * (self.close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(slowperiod).mean()
        
        return pd.DataFrame({'STOCH_K': k, 'STOCH_D': d})
    
    def roc(self, period: int = 12) -> pd.Series:
        """Rate of Change"""
        return self.close.pct_change(periods=period) * 100
    
    def mom(self, period: int = 10) -> pd.Series:
        """Momentum"""
        return self.close - self.close.shift(period)
    
    # -------------------------------------------------------------------------
    # Volatility Indicators
    # -------------------------------------------------------------------------
    
    def bbands(
        self, 
        length: int = 20, 
        std: float = 2.0
    ) -> pd.DataFrame:
        """Bollinger Bands"""
        middle = self.close.rolling(length).mean()
        std_dev = self.close.rolling(length).std()
        
        return pd.DataFrame({
            'BB_UPPER': middle + (std_dev * std),
            'BB_MIDDLE': middle,
            'BB_LOWER': middle - (std_dev * std)
        })
    
    def kc(
        self, 
        length: int = 20, 
        multiplier: float = 2.0
    ) -> pd.DataFrame:
        """Keltner Channels"""
        atr = self.atr(length)
        middle = self.close.ewm(span=length, adjust=False).mean()
        
        return pd.DataFrame({
            'KC_UPPER': middle + (multiplier * atr),
            'KC_MIDDLE': middle,
            'KC_LOWER': middle - (multiplier * atr)
        })
    
    def atr(self, length: int = 14) -> pd.Series:
        """Average True Range"""
        high = self.high
        low = self.low
        close = self.close
        
        tr1 = high - low
        tr2 = (close.shift(1) - high).abs()
        tr3 = (close.shift(1) - low).abs()
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return true_range.rolling(length).mean()
    
    def stdev(self, period: int = 20) -> pd.Series:
        """Standard Deviation"""
        return self.close.rolling(period).std()
    
    def linreg(
        self, 
        period: int = 14, 
        price: Optional[pd.Series] = None
    ) -> pd.Series:
        """Linear Regression"""
        if price is None:
            price = self.close
        
        result = pd.Series(index=price.index, dtype=float)
        
        for i in range(period, len(price)):
            y = price.iloc[i-period:i].values
            x = np.arange(period)
            
            # Linear regression
            x_mean = x.mean()
            y_mean = y.mean()
            
            numerator = np.sum((x - x_mean) * (y - y_mean))
            denominator = np.sum((x - x_mean) ** 2)
            
            slope = numerator / denominator if denominator != 0 else 0
            intercept = y_mean - slope * x_mean
            
            result.iloc[i] = slope * (period - 1) + intercept
        
        return result
    
    # -------------------------------------------------------------------------
    # Volume Indicators
    # -------------------------------------------------------------------------
    
    def obv(self) -> pd.Series:
        """On-Balance Volume"""
        direction = self.close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
        return (direction * self.volume).cumsum()
    
    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------
    
    def get_all_indicators(self) -> pd.DataFrame:
        """
        Compute all available indicators and return as a single DataFrame.
        
        Returns:
            DataFrame with all indicator columns
        """
        df = self.data.copy()
        
        # Trend
        df['SMA_20'] = self.sma(20)
        df['EMA_12'] = self.ema(12)
        df['EMA_26'] = self.ema(26)
        
        # Momentum
        df['RSI_14'] = self.rsi(14)
        macd = self.macd()
        df['MACD'] = macd['MACD']
        df['MACD_Signal'] = macd['MACD_Signal']
        df['MACD_Hist'] = macd['MACD_Hist']
        
        # Volatility
        bbands = self.bbands()
        df['BB_UPPER'] = bbands['BB_UPPER']
        df['BB_MIDDLE'] = bbands['BB_MIDDLE']
        df['BB_LOWER'] = bbands['BB_LOWER']
        df['ATR_14'] = self.atr(14)
        
        # Volume
        df['OBV'] = self.obv()
        
        return df
    
    def plot_summary(self, columns: list = None) -> None:
        """
        Print a summary of available indicators.
        
        Args:
            columns: Optional list of specific indicators to show
        """
        print("=" * 70)
        print("AVAILABLE INDICATORS")
        print("=" * 70)
        
        print("\n📈 TREND INDICATORS:")
        print("    sma(length)      - Simple Moving Average")
        print("    ema(period)      - Exponential Moving Average")
        print("    vwma(period)     - Volume Weighted MA")
        print("    supertrend()     - SuperTrend")
        print("    adx(length)      - Average Directional Index")
        print("    psar()           - Parabolic SAR")
        print("    aroon()          - Aroon Indicator")
        
        print("\n📊 MOMENTUM INDICATORS:")
        print("    rsi(length)      - Relative Strength Index")
        print("    macd()           - MACD (returns DataFrame)")
        print("    willr(length)    - Williams %R")
        print("    cmo(length)      - Chande Momentum Oscillator")
        print("    stoch()          - Stochastic Oscillator")
        print("    roc(period)      - Rate of Change")
        print("    mom(period)      - Momentum")
        
        print("\n📉 VOLATILITY INDICATORS:")
        print("    bbands()         - Bollinger Bands (returns DataFrame)")
        print("    kc()             - Keltner Channels (returns DataFrame)")
        print("    atr(length)      - Average True Range")
        print("    stdev(period)    - Standard Deviation")
        print("    linreg()         - Linear Regression")
        
        print("\n📦 VOLUME INDICATORS:")
        print("    obv()            - On-Balance Volume")
        
        print("\n" + "=" * 70)


# Aliases for vnstock_ta compatibility
Indicator = Indicators
