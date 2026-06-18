"""
Telegram Notification Service
Sends trading alerts to Telegram when position changes occur
"""

import logging
import os
from typing import Optional
from datetime import datetime

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """
    Send trading notifications to Telegram.
    
    Uses Telegram Bot API to send messages when position changes occur.
    """
    
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Initialize Telegram notifier.
        
        Args:
            bot_token: Telegram bot token (defaults to TELEGRAM_BOT_TOKEN env var)
            chat_id: Telegram chat ID (defaults to TELEGRAM_CHAT_ID env var)
        """
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "1670013239")
        
        if not self.bot_token:
            logger.warning("No Telegram bot token provided. Notifications will be mocked.")
            self.api_url = None
        else:
            self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        logger.info(f"Telegram notifier initialized for chat {self.chat_id}")
    
    def send_position_change_alert(
        self,
        symbol: str,
        previous_signal: str,
        current_signal: str,
        confidence: float,
        price: float,
        reasoning: str = ""
    ) -> bool:
        """
        Send alert when trading position changes.
        
        Args:
            symbol: Stock symbol (e.g., 'VNM')
            previous_signal: Previous signal (HOLD, BUY, SELL)
            current_signal: Current signal (HOLD, BUY, SELL)
            confidence: Signal confidence score (0.0 - 1.0)
            price: Stock price at signal
            reasoning: LLM analysis reasoning
            
        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.api_url:
            logger.info(f"[MOCK] Position change alert for {symbol}: {previous_signal} -> {current_signal}")
            return True
        
        # Build message
        emoji = self._get_signal_emoji(current_signal)
        direction = "UP" if current_signal in ["BUY"] else "DOWN" if current_signal in ["SELL"] else "FLAT"
        
        message = f"""
🚨 *TRADING POSITION CHANGE* 🚨

Symbol: *{symbol}*
Direction: {emoji} {direction}

Previous: `{previous_signal}`
Current: `{current_signal}`

Price: ${price:,.2f}
Confidence: {confidence:.1%}

{f'Reasoning:\n`{reasoning}`' if reasoning else ''}

_Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC_
        """.strip()
        
        # Send message
        return self._send_message(message)
    
    def send_signal_alert(
        self,
        symbol: str,
        signal_type: str,
        confidence: float,
        price: float,
        indicators: dict = None
    ) -> bool:
        """
        Send general signal alert.
        
        Args:
            symbol: Stock symbol
            signal_type: BUY, SELL, or HOLD
            confidence: Signal confidence score
            price: Stock price
            indicators: Dictionary of technical indicators
            
        Returns:
            True if message sent successfully
        """
        if not self.api_url:
            logger.info(f"[MOCK] Signal alert for {symbol}: {signal_type} at ${price:,.2f}")
            return True
        
        emoji = self._get_signal_emoji(signal_type)
        
        message = f"""
📊 *TRADING SIGNAL* 📊

Symbol: *{symbol}*
Signal: {emoji} `{signal_type}`

Price: ${price:,.2f}
Confidence: {confidence:.1%}
        """
        
        if indicators:
            message += "\n\n_Indicators:_\n"
            for key, value in indicators.items():
                if isinstance(value, float):
                    message += f"- `{key}`: {value:.2f}\n"
                else:
                    message += f"- `{key}`: {value}\n"
        
        message += f"\n_Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC_"
        
        return self._send_message(message)
    
    def _get_signal_emoji(self, signal_type: str) -> str:
        """Get emoji for signal type"""
        emojis = {
            'BUY': '\U0001f7e2',
            'SELL': '\U0001f534',
            'HOLD': '\u26aa'
        }
        return emojis.get(signal_type.upper(), '\u26aa')
    
    def _send_message(self, message: str) -> bool:
        """Send message to Telegram"""
        try:
            url = f"{self.api_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Telegram message sent successfully to chat {self.chat_id}")
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {str(e)}")
            return False
    
    def test_connection(self) -> dict:
        """Test Telegram connection"""
        if not self.api_url:
            return {
                'status': 'mock',
                'message': 'No bot token configured. Using mock mode.'
            }
        
        try:
            url = f"{self.api_url}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                bot_info = response.json()
                return {
                    'status': 'success',
                    'bot_username': bot_info['result']['username'],
                    'chat_id': self.chat_id
                }
            else:
                return {
                    'status': 'error',
                    'message': f'API error: {response.status_code}'
                }
        
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }


# Singleton instance
_notifier: Optional[TelegramNotifier] = None


def get_telegram_notifier(bot_token: Optional[str] = None, chat_id: Optional[str] = None) -> TelegramNotifier:
    """Get or create Telegram notifier singleton"""
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
    return _notifier
