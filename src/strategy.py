"""
Signal Generation Strategy Module
Evaluates indicators and generates trading signals
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

import pandas as pd


logger = logging.getLogger(__name__)


@dataclass
class TradeSignal:
    """Represents a trading signal"""
    symbol: str
    action: str   # BUY, SELL, HOLD
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    price: Optional[float] = None
    volume: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SignalGenerator:
    """
    Generates trading signals based on technical indicators
    Supports multiple strategies with configurable parameters
    """

    def __init__(self, symbol: str, config: Optional[Dict[str, Any]] = None):
        self.symbol = symbol
        # Default configuration
        self.config = config or {
            'strategies': ['rsi_macd'],
            'thresholds': {
                'rsi_overbought': 70,
                'rsi_oversold': 30,
                'macd_cross_threshold': 0.0
            },
            'cooldown_seconds': 60,
            'min_confidence': 0.5
        }
        
        self.last_signal_time: Optional[datetime] = None
        self.signal_cooldown = self.config.get('cooldown_seconds', 60)
        
        logger.info(f"SignalGenerator initialized for {symbol}")

    def generate_signal(self, evaluated_data: pd.DataFrame) -> Optional[TradeSignal]:
        """
        Generate a trading signal from evaluated data
        
        Args:
            evaluated_data: DataFrame with technical indicators
            
        Returns:
            TradeSignal if action is BUY or SELL, else None (HOLD)
        """
        if evaluated_data.empty:
            logger.warning("No data provided for signal generation")
            return None
        
        # Get the latest bar
        latest = evaluated_data.iloc[-1]
        
        # Check cooldown
        if self._is_in_cooldown():
            logger.debug("In cooldown period, skipping signal")
            return TradeSignal(
                symbol=self.symbol,
                action="HOLD",
                confidence=0.0,
                metadata={'reason': 'cooldown'}
            )
        
        # Evaluate strategies
        strategy_results = []
        
        # RSI + MACD Strategy (default)
        if 'rsi_macd' in self.config.get('strategies', ['rsi_macd']):
            result = self._evaluate_rsi_macd(latest)
            strategy_results.append(('rsi_macd', result))
        
        # Use voting mechanism if multiple strategies exist
        final_signal = self._vote_strategies(strategy_results)
        
        # Update signal time if we got a BUY or SELL
        if final_signal and final_signal.action in ['BUY', 'SELL']:
            self.last_signal_time = datetime.now()
        
        return final_signal

    def _is_in_cooldown(self) -> bool:
        """Check if we're in cooldown period"""
        if self.last_signal_time is None:
            return False
        
        elapsed = (datetime.now() - self.last_signal_time).total_seconds()
        return elapsed < self.signal_cooldown

    def _evaluate_rsi_macd(self, latest: pd.Series) -> Dict[str, Any]:
        """
        Evaluate RSI + MACD strategy
        
        Returns:
            Dictionary with action and confidence
        """
        try:
            # Get indicator values
            rsi = latest.get('RSI')
            macd = latest.get('MACD', 0)
            macd_signal = latest.get('MACD_Signal', 0)
            macd_hist = latest.get('MACD_Hist', 0)
            
            # Check if we have enough data (avoid NaN values)
            if pd.isna(rsi) or pd.isna(macd):
                return {'action': 'HOLD', 'confidence': 0.0, 'reason': 'insufficient_data'}
            
            thresholds = self.config.get('thresholds', {})
            rsi_overbought = thresholds.get('rsi_overbought', 70)
            rsi_oversold = thresholds.get('rsi_oversold', 30)
            
            buy_signals = []
            sell_signals = []
            
            # Buy conditions
            if rsi < rsi_oversold and macd_hist > 0:
                buy_signals.append(('rsi_oversold_macd_positive', 0.7))
            if rsi < rsi_oversold and macd > macd_signal:
                buy_signals.append(('rsi_cross_below_macd', 0.6))
            if macd_hist > 0 and macd > macd_signal:
                buy_signals.append(('macd_bullish_cross', 0.5))
            
            # Sell conditions
            if rsi > rsi_overbought and macd_hist < 0:
                sell_signals.append(('rsi_overbought_macd_negative', 0.7))
            if rsi > rsi_overbought and macd < macd_signal:
                sell_signals.append(('rsi_cross_above_macd', 0.6))
            if macd_hist < 0 and macd < macd_signal:
                sell_signals.append(('macd_bearish_cross', 0.5))
            
            # Determine signal based on signals
            if buy_signals:
                max_confidence = max(conf for _, conf in buy_signals)
                return {
                    'action': 'BUY',
                    'confidence': max_confidence,
                    'reason': f"Buy signals: {[s[0] for s in buy_signals]}"
                }
            elif sell_signals:
                max_confidence = max(conf for _, conf in sell_signals)
                return {
                    'action': 'SELL',
                    'confidence': max_confidence,
                    'reason': f"Sell signals: {[s[0] for s in sell_signals]}"
                }
            else:
                return {
                    'action': 'HOLD',
                    'confidence': 0.0,
                    'reason': 'no_signals'
                }
        
        except Exception as e:
            logger.error(f"Error evaluating RSI+MACD: {str(e)}")
            return {'action': 'HOLD', 'confidence': 0.0, 'reason': f'error: {str(e)}'}

    def _vote_strategies(self, strategy_results: list) -> Optional[TradeSignal]:
        """
        Vote between multiple strategies
        
        Args:
            strategy_results: List of (strategy_name, result_dict) tuples
            
        Returns:
            Final TradeSignal or None
        """
        buy_score = 0
        sell_score = 0
        max_confidence = 0.0
        winning_action = None
        
        for strategy_name, result in strategy_results:
            if result.get('action') == 'BUY':
                buy_score += result.get('confidence', 0)
                if result['confidence'] > max_confidence:
                    max_confidence = result['confidence']
                    winning_action = 'BUY'
            elif result.get('action') == 'SELL':
                sell_score += result.get('confidence', 0)
                if result['confidence'] > max_confidence:
                    max_confidence = result['confidence']
                    winning_action = 'SELL'
        
        # Determine final signal based on voting
        min_confidence = self.config.get('min_confidence', 0.5)
        
        if buy_score > sell_score and winning_action == 'BUY' and max_confidence >= min_confidence:
            return TradeSignal(
                symbol=self.symbol,
                action='BUY',
                confidence=max_confidence,
                metadata={'vote': f'buy:{buy_score:.2f} vs sell:{sell_score:.2f}'}
            )
        elif sell_score > buy_score and winning_action == 'SELL' and max_confidence >= min_confidence:
            return TradeSignal(
                symbol=self.symbol,
                action='SELL',
                confidence=max_confidence,
                metadata={'vote': f'buy:{buy_score:.2f} vs sell:{sell_score:.2f}'}
            )
        else:
            return TradeSignal(
                symbol=self.symbol,
                action='HOLD',
                confidence=0.0,
                metadata={'vote': f'buy:{buy_score:.2f} vs sell:{sell_score:.2f}'}
            )
