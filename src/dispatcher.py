"""
Signal Dispatch Module
Sends trading signals to execution interfaces
"""

import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import json

import requests


logger = logging.getLogger(__name__)


@dataclass
class DispatchResult:
    success: bool
    status_code: Optional[int] = None
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class SignalDispatcher:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
              "execution_url": None,
              "api_key": None,
              "secret_key": None,
              "timeout": 10,
              "max_retries": 3,
              "retry_delay": 1.0,
              "webhook_url": None,
              "signature_method": "none"
          }
        
        self.execution_url = self.config.get("execution_url")
        self.api_key = self.config.get("api_key")
        self.secret_key = self.config.get("secret_key")
        self.timeout = self.config.get("timeout", 10)
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 1.0)
        self.webhook_url = self.config.get("webhook_url")
        
        self.failure_count = 0
        self.circuit_breaker_threshold = self.config.get("circuit_breaker_threshold", 5)
        self.circuit_open = False
        self.last_failure_time: Optional[datetime] = None
        
        logger.info("SignalDispatcher initialized")

    def dispatch(self, signal) -> DispatchResult:
        if self.circuit_open:
            logger.warning("Circuit breaker is OPEN. Signal not dispatched.")
            return DispatchResult(
                success=False,
                error_message="Circuit breaker open"
              )
        
        payload = self._build_payload(signal)
        
        if self.execution_url:
            result = self._dispatch_via_api(payload)
            if result.success:
                return result
        
        if self.webhook_url:
            result = self._dispatch_via_webhook(payload)
            if result.success:
                return result
        
        logger.warning("No execution interface configured")
        return DispatchResult(
            success=False,
            error_message="No execution interface configured"
          )

    def _build_payload(self, signal) -> Dict[str, Any]:
        return {
              "action": signal.action,
              "symbol": signal.symbol,
              "timestamp": signal.timestamp.isoformat(),
              "confidence": signal.confidence,
              "price": signal.price,
              "volume": signal.volume,
              "metadata": signal.metadata
          }

    def _dispatch_via_api(self, payload: Dict[str, Any]) -> DispatchResult:
        for attempt in range(self.max_retries):
            try:
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                response = requests.post(
                    self.execution_url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                 )
                
                if response.status_code in [200, 201]:
                    logger.info(f"Signal dispatched successfully: {payload['action']}")
                    self.failure_count = 0
                    self.circuit_open = False
                    
                    return DispatchResult(
                        success=True,
                        status_code=response.status_code,
                        response_data=response.json() if response.text else None
                     )
                else:
                    logger.warning(
                        f"API returned status {response.status_code}: "
                        f"{response.text}"
                     )
                    
            except requests.exceptions.Timeout:
                logger.error("API request timed out")
            except requests.exceptions.ConnectionError:
                logger.error("Connection error to API")
            except Exception as e:
                logger.error(f"Dispatch failed: {str(e)}")
            
            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (2 ** attempt)
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
        
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.circuit_breaker_threshold:
            logger.error("Circuit breaker OPEN due to failures")
            self.circuit_open = True
        
        return DispatchResult(
            success=False,
            error_message="All retries failed"
          )

    def _dispatch_via_webhook(self, payload: Dict[str, Any]) -> DispatchResult:
        try:
            headers = {"Content-Type": "application/json"}
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
             )
            
            if response.status_code in [200, 201]:
                logger.info("Webhook dispatched successfully")
                return DispatchResult(
                    success=True,
                    status_code=response.status_code,
                    response_data=response.json() if response.text else None
                 )
            else:
                logger.warning(f"Webhook returned status {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.error("Webhook request timed out")
        except requests.exceptions.ConnectionError:
            logger.error("Connection error to webhook")
        except Exception as e:
            logger.error(f"Webhook dispatch failed: {str(e)}")
        
        return DispatchResult(
            success=False,
            error_message="Webhook dispatch failed"
          )
