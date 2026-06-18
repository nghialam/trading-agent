"""
LLM Analysis Service
Analyzes trading signals using LLM to determine if they are qualified or fake
Uses multiple indicators including Pocket Pivot for position determination
"""

import logging
import os
from typing import Optional, Dict, List
from datetime import datetime

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

logger = logging.getLogger(__name__)


class LLMAnalyzer:
    """
    Analyzes trading signals using LLM to determine signal quality.
    
    Uses OpenAI API (or compatible) to analyze market context,
    indicators, and price action to verify if signals are qualified.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize LLM analyzer.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model name to use for analysis
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        
        if not self.api_key:
            logger.warning("No OpenAI API key provided. LLM analysis will return mock results.")
        
        # Initialize OpenAI client if key is available
        if HAS_OPENAI and self.api_key:
            openai.api_key = self.api_key
            self.client = openai.OpenAI()
        else:
            self.client = None
    
    def analyze_signal(
        self,
        symbol: str,
        signal_type: str,
        confidence: float,
        indicators: Dict,
        pocket_pivot: Dict,
        price_context: Dict
    ) -> Dict:
        """
        Analyze a trading signal using LLM to determine if it's qualified.
        
        Args:
            symbol: Stock symbol
            signal_type: BUY, SELL, or HOLD
            confidence: Signal confidence score (0.0 - 1.0)
            indicators: Dictionary of technical indicators (RSI, MACD, etc.)
            pocket_pivot: Pocket pivot analysis result
            price_context: Price context (current price, previous high/low, etc.)
            
        Returns:
            Dictionary with LLM verdict and reasoning
        """
        if not self.client or not self.api_key:
            return self._mock_analysis(symbol, signal_type, indicators, pocket_pivot)
        
        # Build prompt for LLM
        prompt = self._build_analysis_prompt(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            indicators=indicators,
            pocket_pivot=pocket_pivot,
            price_context=price_context
        )
        
        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=500
            )
            
            # Parse LLM response
            llm_text = response.choices[0].message.content
            return self._parse_llm_response(llm_text, symbol)
        
        except Exception as e:
            logger.error(f"LLM analysis failed for {symbol}: {str(e)}")
            return self._mock_analysis(symbol, signal_type, indicators, pocket_pivot)
    
    def _build_analysis_prompt(
        self,
        symbol: str,
        signal_type: str,
        confidence: float,
        indicators: Dict,
        pocket_pivot: Dict,
        price_context: Dict
    ) -> str:
        """Build prompt for LLM analysis"""
        
        # Format indicators
        indicators_str = "\n".join([f"   - {k}: {v:.2f}" if isinstance(v, float) else f"   - {k}: {v}" 
                                     for k, v in indicators.items()])
        
        # Build prompt
        prompt = f"""Analyze the following trading signal for {symbol} and determine if it is QUALIFIED, WEAK, or FAKE.

SIGNAL CONTEXT:
- Signal Type: {signal_type}
- Confidence Score: {confidence:.2%}

TECHNICAL INDICATORS:
{indicators_str}

POCKET PIVOT ANALYSIS (1h timeframe):
- Pivot Type: {pocket_pivot.get('pivot_type', 'NONE')}
- Volume Ratio: {pocket_pivot.get('volume_ratio', 0):.2f}x
- Valid Signal: {'Yes' if pocket_pivot.get('is_valid') else 'No'}

PRICE CONTEXT:
- Current Price: ${price_context.get('close_price', 'N/A')}
- Previous Day High: ${price_context.get('prev_high', 'N/A')}
- Previous Day Low: ${price_context.get('prev_low', 'N/A')}

ANALYSIS CRITERIA:
1. QUALIFIED: Multiple indicators align (RSI + MACD + Pocket Pivot confirm signal)
2. WEAK: Some indicators support but others contradict or are neutral
3. FAKE: Indicators contradict the signal or show divergence

Please provide your analysis in this format:
VERDICT: [QUALIFIED|WEAK|FAKE]
CONFIDENCE: [0.0-1.0]
REASONING: [Brief explanation of why]
RISK_LEVEL: [LOW|MEDIUM|HIGH]
NOTES: [Any additional observations]"""
        
        return prompt
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for LLM analysis"""
        return """You are an expert trading analyst specializing in Vietnamese stock market technical analysis.

Your task is to analyze trading signals and determine if they are:
- QUALIFIED: Strong multi-indicator confirmation, high probability of success
- WEAK: Mixed signals, moderate probability
- FAKE: Contradictory indicators, likely false signal

Use the following criteria:
1. RSI: Below 30 = oversold (bullish), Above 70 = overbought (bearish)
2. MACD: MACD > Signal = bullish crossover, MACD < Signal = bearish crossover
3. Pocket Pivot: BULLISH_PIVOT with high volume confirms upward momentum
4. Volume: Ratio > 1.5x average indicates strong conviction

Be thorough but concise in your analysis."""
    
    def _parse_llm_response(self, llm_text: str, symbol: str) -> Dict:
        """Parse LLM response text into structured data"""
        verdict = "WEAK"
        confidence = 0.5
        reasoning = ""
        risk_level = "MEDIUM"
        notes = ""
        
        # Extract verdict
        for line in llm_text.split('\n'):
            if line.upper().startswith('VERDICT:'):
                verdict = line.split(':')[1].strip().upper()
            elif line.upper().startswith('CONFIDENCE:'):
                try:
                    confidence = float(line.split(':')[1].strip())
                except (ValueError, IndexError):
                    pass
            elif line.upper().startswith('REASONING:'):
                reasoning = line.split(':', 1)[1].strip() if ':' in line else line.strip()
            elif line.upper().startswith('RISK_LEVEL:'):
                risk_level = line.split(':')[1].strip().upper()
            elif line.upper().startswith('NOTES:'):
                notes = line.split(':', 1)[1].strip() if ':' in line else line.strip()
        
        return {
            'symbol': symbol,
            'verdict': verdict,
            'confidence': confidence,
            'reasoning': reasoning,
            'risk_level': risk_level,
            'notes': notes
        }
    
    def _mock_analysis(
        self,
        symbol: str,
        signal_type: str,
        indicators: Dict,
        pocket_pivot: Dict
    ) -> Dict:
        """
        Generate mock analysis when LLM API is not available.
        
        Uses rule-based logic to simulate LLM-style analysis.
        """
        # Rule-based verdict
        rsi = indicators.get('RSI', 50)
        macd = indicators.get('MACD', 0)
        macd_signal = indicators.get('MACD_Signal', 0)
        pivot = pocket_pivot.get('pivot_type', 'NONE')
        
        # Determine verdict based on rules
        if signal_type == "BUY":
            if rsi < 35 and macd > macd_signal and pivot == "BULLISH_PIVOT":
                verdict = "QUALIFIED"
                confidence = 0.85
            elif rsi < 40 and macd > macd_signal:
                verdict = "WEAK"
                confidence = 0.65
            else:
                verdict = "FAKE"
                confidence = 0.35
        
        elif signal_type == "SELL":
            if rsi > 65 and macd < macd_signal and pivot == "BEARISH_PIVOT":
                verdict = "QUALIFIED"
                confidence = 0.85
            elif rsi > 60 and macd < macd_signal:
                verdict = "WEAK"
                confidence = 0.65
            else:
                verdict = "FAKE"
                confidence = 0.35
        
        else:  # HOLD
            verdict = "QUALIFIED" if abs(rsi - 50) < 15 else "WEAK"
            confidence = 0.70
        
        # Generate reasoning
        reasoning_parts = []
        if rsi < 30:
            reasoning_parts.append("RSI indicates oversold conditions")
        elif rsi > 70:
            reasoning_parts.append("RSI indicates overbought conditions")
        
        if macd > macd_signal:
            reasoning_parts.append("MACD shows bullish crossover")
        elif macd < macd_signal:
            reasoning_parts.append("MACD shows bearish crossover")
        
        if pivot == "BULLISH_PIVOT":
            reasoning_parts.append("Pocket Pivot confirms bullish momentum")
        elif pivot == "BEARISH_PIVOT":
            reasoning_parts.append("Pocket Pivot confirms bearish momentum")
        
        return {
            'symbol': symbol,
            'verdict': verdict,
            'confidence': confidence,
            'reasoning': "; ".join(reasoning_parts) if reasoning_parts else "Mixed signals detected",
            'risk_level': "LOW" if verdict == "QUALIFIED" else ("MEDIUM" if verdict == "WEAK" else "HIGH"),
            'notes': f"Mock analysis (LLM API not available)"
        }


# Singleton instance
_llm_analyzer: Optional[LLMAnalyzer] = None


def get_llm_analyzer(api_key: Optional[str] = None) -> LLMAnalyzer:
    """Get or create LLM analyzer singleton"""
    global _llm_analyzer
    if _llm_analyzer is None:
        _llm_analyzer = LLMAnalyzer(api_key=api_key)
    return _llm_analyzer
