"""
Scanner Service
Multi-threaded stock market scanner for 24/7 operation
Monitors watchlist with high-frequency updates
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from database.models import Watchlist, Signal, SystemLog, ScannerConfig
from database.config import SessionLocal, get_db
from src.technical_indicators import Indicators
from vnstock import Quote


logger = logging.getLogger(__name__)


class ScannerService:
    """
    Main scanner service that monitors stocks and generates trading signals.

    Features:
      - Multi-threaded scanning for watchlist
      - Priority-based update frequency (VN30 high priority)
      - Automated error recovery with retry logic
      - Real-time configuration reload
    """

    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running = False
        self.watchlist: List[Watchlist] = []
        self.config: Dict[str, str] = {}
        self._lock = threading.Lock()

        # Scanner parameters (reloadable)
        self.scan_interval_seconds = 30     # Default scan interval
        self.high_priority_interval = 10    # VN30 stocks
        self.low_priority_interval = 60    # Other stocks

        logger.info(f"ScannerService initialized with {max_workers} workers")

    def load_watchlist(self, db_session) -> List[Watchlist]:
        """Load active watchlist from database"""
        return db_session.query(Watchlist).filter_by(enabled=True).all()

    def load_config(self, db_session) -> Dict[str, str]:
        """Load scanner configuration from database"""
        configs = {}
        for config in db_session.query(ScannerConfig).all():
            configs[config.key] = config.value
        return configs

    def reload_config(self):
        """Reload configuration from database (call periodically)"""
        db = SessionLocal()
        try:
            self.config = self.load_config(db)
            # Update scan intervals based on config
            if "scan_interval" in self.config:
                self.scan_interval_seconds = int(self.config["scan_interval"])
            if "high_priority_interval" in self.config:
                self.high_priority_interval = int(self.config["high_priority_interval"])
            logger.info("Configuration reloaded")
        finally:
            db.close()

    def scan_stock(self, stock: Watchlist):
        """
        Scan a single stock and generate signals.
        Runs in separate thread for parallel processing.
        """
        symbol = stock.symbol
        try:
            # Fetch historical data - use 90 days to ensure >= 50 trading bars
            logger.debug(f"Fetching data for {symbol}...")
            df = self._fetch_historical_data(symbol, days=90)

            if df.empty or len(df) < 50:
                logger.warning(f"Insufficient data for {symbol}: {len(df)} bars (need >= 50)")
                return

            # Compute indicators
            indicator = Indicators(df)
            rsi = indicator.rsi(length=14).iloc[-1]
            macd_df = indicator.macd()
            macd = macd_df['MACD'].iloc[-1]
            macd_signal = macd_df['MACD_Signal'].iloc[-1]

            # Generate signal based on indicators
            signal_type, confidence = self._evaluate_signals(
                rsi=rsi,
                macd=macd,
                macd_signal=macd_signal,
                close_price=df['close'].iloc[-1]
            )

            # Save signal to database
            self._save_signal(
                symbol=symbol,
                signal_type=signal_type,
                confidence_score=confidence,
                price_at_signal=df['close'].iloc[-1],
                indicators={
                    'RSI': rsi,
                    'MACD': macd,
                    'MACD_Signal': macd_signal
                }
            )

            logger.info(
                f"Signal generated: {symbol} -> {signal_type} "
                f"(confidence: {confidence:.2%})"
            )

        except Exception as e:
            logger.error(f"Error scanning {symbol}: {str(e)}")
            self._log_error(symbol=symbol, error=str(e))

    def _fetch_historical_data(self, symbol: str, days: int = 90) -> pd.DataFrame:
        """Fetch historical OHLCV data from vnstock"""
        try:
            # Using vnstock API
            quote = Quote(source="VCI", symbol=symbol)
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            df = quote.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval="1D"
            )

            # Normalize column names
            if not df.empty:
                df.columns = [col.lower() for col in df.columns]
                # Ensure required columns exist
                required = ['time', 'open', 'high', 'low', 'close', 'volume']
                if all(col in df.columns for col in required):
                    df = df.set_index('time')
                    return df

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {str(e)}")
            return pd.DataFrame()

    def _evaluate_signals(
        self,
        rsi: float,
        macd: float,
        macd_signal: float,
        close_price: float
    ) -> tuple:
        """
        Evaluate technical indicators to generate trading signals.

        Returns:
            (signal_type, confidence) tuple
        """
        # Default HOLD signal
        signal_type = "HOLD"
        confidence = 0.0

        # RSI + MACD strategy
        if rsi < 30 and macd > macd_signal:
            # Oversold + MACD crossover -> BUY
            signal_type = "BUY"
            confidence = 0.5 + (30 - rsi) / 100    # Higher when more oversold
        elif rsi > 70 and macd < macd_signal:
            # Overbought + MACD reverse crossover -> SELL
            signal_type = "SELL"
            confidence = 0.5 + (rsi - 70) / 100    # Higher when more overbought
        else:
            # Neutral
            signal_type = "HOLD"
            confidence = abs(rsi - 50) / 100    # Closer to 50 = lower confidence

        # Cap confidence at 95%
        confidence = min(confidence, 0.95)

        return signal_type, confidence

    def _save_signal(
        self,
        symbol: str,
        signal_type: str,
        confidence_score: float,
        price_at_signal: float,
        indicators: Dict
    ):
        """Save trading signal to database - converts numpy types to native Python types"""
        
        # Convert numpy floats to native Python floats for PostgreSQL compatibility
        try:
            confidence = float(confidence_score) if isinstance(confidence_score, (float,)) else confidence_score
            price = float(price_at_signal) if isinstance(price_at_signal, (float,)) else price_at_signal
        except (ValueError, TypeError):
            confidence = 0.0
            price = 0.0
        
        # Convert numpy values in indicators dict to native Python types
        clean_indicators = {}
        for k, v in (indicators or {}).items():
            if isinstance(v, bool):
                clean_indicators[k] = bool(v)
            else:
                try:
                    clean_indicators[k] = float(v)
                except (ValueError, TypeError):
                    clean_indicators[k] = v
        
        db = SessionLocal()
        try:
            signal = Signal(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                signal_type=signal_type,
                confidence_score=confidence,
                price_at_signal=price,
                indicators=clean_indicators,
                metadata={'source': 'scanner_service'}
            )
            db.add(signal)
            db.commit()
            logger.debug(f"Signal saved: {symbol} {signal_type}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save signal for {symbol}: {str(e)}")
        finally:
            db.close()

    def _log_error(self, symbol: str, error: str):
        """Log error to database"""
        db = SessionLocal()
        try:
            log_entry = SystemLog(
                timestamp=datetime.utcnow(),
                level="ERROR",
                component="scanner",
                message=f"Scan failed for {symbol}",
                details={'error': error, 'symbol': symbol}
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to log error: {str(e)}")
        finally:
            db.close()

    def scan_single_stock(self, symbol: str):
        """Scan a single stock (for manual trigger)"""
        db = SessionLocal()
        try:
            stock = db.query(Watchlist).filter_by(symbol=symbol, enabled=True).first()
            if stock:
                self.scan_stock(stock)
            else:
                logger.warning(f"Stock {symbol} not found or disabled")
        finally:
            db.close()

    def run(self):
        """
        Main scanner loop.
        Runs continuously, scanning all watchlist stocks.
        This method blocks until stop() is called.
        """
        if self.running:
            logger.warning("Scanner already running")
            return

        self.running = True
        logger.info("Scanner service started")

        try:
            while self.running:
                start_time = time.time()

                # Reload config periodically (every 5 minutes)
                if not hasattr(self, '_last_config_reload'):
                    self._last_config_reload = 0
                if time.time() - self._last_config_reload > 300:
                    self.reload_config()
                    self._last_config_reload = time.time()

                # Load watchlist
                db = SessionLocal()
                try:
                    self.watchlist = self.load_watchlist(db)
                finally:
                    db.close()

                if not self.watchlist:
                    logger.warning("No active stocks in watchlist")
                    time.sleep(self.scan_interval_seconds)
                    continue

                # Scan all stocks in parallel
                futures = []
                for stock in self.watchlist:
                    future = self.executor.submit(self.scan_stock, stock)
                    futures.append(future)

                # Wait for all scans to complete
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"Scanner thread error: {str(e)}")

                # Calculate sleep time
                elapsed = time.time() - start_time
                sleep_time = max(0, self.scan_interval_seconds - elapsed)

                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("Scanner service stopped by user")
        finally:
            self.stop()

    def run_in_background_thread(self):
        """Start the scanner in a background daemon thread (for production use)."""
        if self.running:
            logger.warning("Scanner already running")
            return
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        logger.info("Scanner service started in background thread")

    def stop(self):
        """Stop the scanner service"""
        self.running = False
        logger.info("Stopping scanner service...")
        try:
            self.executor.shutdown(wait=False, cancel_futures=True)
        except Exception as e:
            logger.error(f"Error shutting down executor: {str(e)}")
        logger.info("Scanner service stopped")


# Singleton instance
scanner_instance: Optional[ScannerService] = None


def get_scanner() -> ScannerService:
    """Get or create scanner singleton"""
    global scanner_instance
    if scanner_instance is None:
        scanner_instance = ScannerService()
    return scanner_instance
