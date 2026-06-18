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

from database.models import (
    Watchlist, Signal, SystemLog, ScannerConfig,
    SignalReview, DailySummary, PocketPivotData
)
from database.config import SessionLocal
from src.technical_indicators import Indicators
from src.llm_analysis import get_llm_analyzer
from src.telegram_notifier import get_telegram_notifier
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
        - Multi-timeframe analysis (1D + 1H)
        - LLM signal verification
        - Pocket Pivot indicator
        - Daily summary generation
    """

    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running = False
        self.watchlist: List[Watchlist] = []
        self.config: Dict[str, str] = {}
        self._lock = threading.Lock()

        # Scanner parameters (reloadable)
        self.scan_interval_seconds = 30
        self.high_priority_interval = 10
        self.low_priority_interval = 60

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
            if "scan_interval" in self.config:
                self.scan_interval_seconds = int(self.config["scan_interval"])
            if "high_priority_interval" in self.config:
                self.high_priority_interval = int(self.config["high_priority_interval"])
            logger.info("Configuration reloaded")
        finally:
            db.close()

    def scan_stock(self, stock: Watchlist):
        """
        Scan a single stock and generate signals with multi-timeframe analysis.

        Features:
            - Fetches both 1D (90 days) and 1H (5 days) data for multi-timeframe analysis
            - Computes Pocket Pivot indicator on 1h timeframe for position determination
            - Uses LLM to analyze and verify signals (QUALIFIED/WEAK/FAKE verdict)
            - Stores curated signal reviews for position changes
            - Generates daily summaries with notable events

        Runs in separate thread for parallel processing.
        """
        symbol = stock.symbol
        try:
            logger.debug(f"Starting multi-timeframe scan for {symbol}...")

            # Fetch 1D data (90 days) for main signal generation
            df_1d = self._fetch_historical_data(symbol, days=90, interval="1D")

            if df_1d.empty or len(df_1d) < 50:
                logger.warning(f"Insufficient 1D data for {symbol}: {len(df_1d)} bars (need >= 50)")
                return

            # Fetch 1H data (5 days) for Pocket Pivot analysis
            df_1h = self._fetch_historical_data(symbol, days=5, interval="1H")

            # Compute 1D indicators
            indicator_1d = Indicators(df_1d)
            rsi = indicator_1d.rsi(length=14).iloc[-1]
            macd_df = indicator_1d.macd()
            macd = macd_df['MACD'].iloc[-1]
            macd_signal = macd_df['MACD_Signal'].iloc[-1]

            # Compute Pocket Pivot on 1H timeframe
            pocket_pivot_result = {'pivot_type': 'NONE', 'volume_ratio': 0.0, 'is_valid': False}
            if not df_1h.empty and len(df_1h) >= 10:
                try:
                    from src.technical_indicators import pocket_pivot
                    pivot_data = pocket_pivot(df_1h, lookback=5)
                    pocket_pivot_result = pivot_data

                    # Save Pocket Pivot data to database
                    self._save_pocket_pivot(symbol, pivot_data, df_1h)
                except Exception as e:
                    logger.warning(f"Pocket Pivot calculation failed for {symbol}: {str(e)}")

            # Generate signal based on 1D indicators
            signal_type, base_confidence = self._evaluate_signals(
                rsi=rsi,
                macd=macd,
                macd_signal=macd_signal,
                close_price=df_1d['close'].iloc[-1]
            )

            # Prepare price context for LLM analysis
            price_context = {
                'close_price': float(df_1d['close'].iloc[-1]),
                'prev_high': float(df_1d['high'].iloc[-2]) if len(df_1d) > 1 else 0,
                'prev_low': float(df_1d['low'].iloc[-2]) if len(df_1d) > 1 else 0,
                'volume_ratio': float(df_1d['volume'].iloc[-1] / df_1d['volume'].rolling(5).mean().iloc[-1])
            }

            # LLM Analysis to verify signal
            llm_verdict = {'verdict': 'WEAK', 'confidence': 0.5, 'reasoning': 'Mock analysis'}
            try:
                analyzer = get_llm_analyzer()
                llm_verdict = analyzer.analyze_signal(
                    symbol=symbol,
                    signal_type=signal_type,
                    confidence=base_confidence,
                    indicators={
                        'RSI': rsi,
                        'MACD': macd,
                        'MACD_Signal': macd_signal
                    },
                    pocket_pivot=pocket_pivot_result,
                    price_context=price_context
                )
                logger.info(f"LLM analysis for {symbol}: {llm_verdict.get('verdict')} (confidence: {llm_verdict.get('confidence', 0):.2%})")
            except Exception as e:
                logger.warning(f"LLM analysis failed for {symbol}: {str(e)}")

            # Adjust confidence based on LLM verdict
            final_confidence = base_confidence * llm_verdict.get('confidence', 0.5)
            final_confidence = min(final_confidence, 0.95)

            # Determine if this is a position change (HOLD -> BUY/SELL or vice versa)
            previous_signal = self._get_last_signal_type(symbol)
            is_position_change = previous_signal and previous_signal != signal_type

            # Save main signal to database
            self._save_signal(
                symbol=symbol,
                signal_type=signal_type,
                confidence_score=final_confidence,
                price_at_signal=df_1d['close'].iloc[-1],
                indicators={
                    'RSI': rsi,
                    'MACD': macd,
                    'MACD_Signal': macd_signal,
                    'Pocket_Pivot': pocket_pivot_result.get('pivot_type'),
                    'Volume_Ratio': pocket_pivot_result.get('volume_ratio')
                },
                llm_verdict=llm_verdict
            )

# If position change detected, save curated review and send notification
            if is_position_change:
                self._save_signal_review(
                    symbol=symbol,
                    previous_signal=previous_signal,
                    current_signal=signal_type,
                    llm_analysis=llm_verdict,
                    indicators={
                         'RSI': rsi,
                         'MACD': macd,
                         'MACD_Signal': macd_signal
                     }
                 )
                logger.info(f"POSITION CHANGE detected for {symbol}: {previous_signal} -> {signal_type}")
                
                # Send Telegram notification
                try:
                    notifier = get_telegram_notifier()
                    notifier.send_position_change_alert(
                        symbol=symbol,
                        previous_signal=previous_signal,
                        current_signal=signal_type,
                        confidence=final_confidence,
                        price=df_1d['close'].iloc[-1],
                        reasoning=llm_verdict.get('reasoning', '')
                    )
                except Exception as e:
                    logger.warning(f"Failed to send Telegram notification for {symbol}: {str(e)}")

            logger.info(
                f"Signal generated: {symbol} -> {signal_type} "
                f"(confidence: {final_confidence:.2%}, LLM: {llm_verdict.get('verdict')})"
            )

            # Generate daily summary (once per day)
            self._generate_daily_summary(symbol, df_1d, signal_type)

        except Exception as e:
            logger.error(f"Error scanning {symbol}: {str(e)}")
            self._log_error(symbol=symbol, error=str(e))

    def _fetch_historical_data(self, symbol: str, days: int = 90, interval: str = "1D") -> pd.DataFrame:
        """Fetch historical OHLCV data from vnstock"""
        try:
            quote = Quote(source="VCI", symbol=symbol)
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            df = quote.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval=interval
            )

            if not df.empty:
                df.columns = [col.lower() for col in df.columns]
                required = ['time', 'open', 'high', 'low', 'close', 'volume']
                if all(col in df.columns for col in required):
                    df = df.set_index('time')
                    return df

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol} ({interval}): {str(e)}")
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
        signal_type = "HOLD"
        confidence = 0.0

        # RSI + MACD strategy
        if rsi < 30 and macd > macd_signal:
            signal_type = "BUY"
            confidence = 0.5 + (30 - rsi) / 100
        elif rsi > 70 and macd < macd_signal:
            signal_type = "SELL"
            confidence = 0.5 + (rsi - 70) / 100
        else:
            signal_type = "HOLD"
            confidence = abs(rsi - 50) / 100

        confidence = min(confidence, 0.95)

        return signal_type, confidence

    def _save_signal(
        self,
        symbol: str,
        signal_type: str,
        confidence_score: float,
        price_at_signal: float,
        indicators: Dict,
        llm_verdict: Optional[Dict] = None
    ):
        """Save trading signal to database - converts numpy types to native Python types"""

        try:
            confidence = float(confidence_score) if isinstance(confidence_score, (float,)) else confidence_score
            price = float(price_at_signal) if isinstance(price_at_signal, (float,)) else price_at_signal
        except (ValueError, TypeError):
            confidence = 0.0
            price = 0.0

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
            metadata = {'source': 'scanner_service'}
            if llm_verdict:
                metadata['llm_verdict'] = llm_verdict.get('verdict', 'WEAK')
                metadata['llm_confidence'] = llm_verdict.get('confidence', 0.5)
                metadata['llm_reasoning'] = llm_verdict.get('reasoning', '')

            signal = Signal(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                signal_type=signal_type,
                confidence_score=confidence,
                price_at_signal=price,
                indicators=clean_indicators,
                extra_metadata=metadata
            )
            db.add(signal)
            db.commit()
            logger.debug(f"Signal saved: {symbol} {signal_type}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save signal for {symbol}: {str(e)}")
        finally:
            db.close()

    def _save_signal_review(
        self,
        symbol: str,
        previous_signal: str,
        current_signal: str,
        llm_analysis: Dict,
        indicators: Dict
    ):
        """Save curated signal review for position changes"""
        db = SessionLocal()
        try:
            review = SignalReview(
                symbol=symbol,
                previous_signal=previous_signal,
                current_signal=current_signal,
                is_position_change=True,
                llm_analysis=llm_analysis,
                llm_verdict=llm_analysis.get('verdict', 'WEAK'),
                llm_confidence=llm_analysis.get('confidence', 0.5),
                analysis_notes=f"Position changed from {previous_signal} to {current_signal}"
            )
            db.add(review)
            db.commit()
            logger.info(f"Signal review saved: {symbol} {previous_signal} -> {current_signal}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save signal review for {symbol}: {str(e)}")
        finally:
            db.close()

    def _save_pocket_pivot(
        self,
        symbol: str,
        pivot_data: Dict,
        df_1h: pd.DataFrame
    ):
        """Save Pocket Pivot data to database"""
        db = SessionLocal()
        try:
            pivot = PocketPivotData(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                pivot_type=pivot_data.get('pivot_type', 'NONE'),
                pivot_price=float(df_1h['close'].iloc[-1]),
                volume_ratio=pivot_data.get('volume_ratio', 0.0),
                is_valid=pivot_data.get('is_valid', False),
                previous_high=float(df_1h['high'].iloc[-2]) if len(df_1h) > 1 else 0,
                previous_low=float(df_1h['low'].iloc[-2]) if len(df_1h) > 1 else 0,
                context_data={'volume': float(df_1h['volume'].iloc[-1])}
            )
            db.add(pivot)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save Pocket Pivot data for {symbol}: {str(e)}")
        finally:
            db.close()

    def _generate_daily_summary(
        self,
        symbol: str,
        df_1d: pd.DataFrame,
        signal_type: str
    ):
        """Generate daily summary with notable events and trading notes"""
        db = SessionLocal()
        try:
            today = datetime.utcnow().date()

            existing = (
                db.query(DailySummary)
                .filter(DailySummary.date >= today, DailySummary.symbol == symbol)
                .first()
            )
            if existing:
                return

            close_price = float(df_1d['close'].iloc[-1])
            open_price = float(df_1d['open'].iloc[0])
            high_price = float(df_1d['high'].max())
            low_price = float(df_1d['low'].min())
            total_volume = float(df_1d['volume'].sum())

            price_change = ((close_price - open_price) / open_price) * 100

            notable_events = []
            if price_change > 3:
                notable_events.append("Strong bullish day")
            elif price_change < -3:
                notable_events.append("Strong bearish day")

            summary_text = (
                f"{symbol} closed at ${close_price:.2f} ({price_change:+.2%}). "
                f"Day range: ${low_price:.2f} - ${high_price:.2f}. "
                f"Total volume: {total_volume:,.0f}. Signal: {signal_type}."
            )

            summary = DailySummary(
                date=datetime.combine(today, datetime.min.time()),
                symbol=symbol,
                summary_text=summary_text,
                notable_events=notable_events,
                trading_notes=f"Monitor for continuation based on {signal_type} signal",
                market_conditions={'trend': 'bullish' if price_change > 0 else 'bearish'},
                volume_analysis={'total_volume': total_volume, 'avg_volume': float(df_1d['volume'].mean())}
            )
            db.add(summary)
            db.commit()
            logger.info(f"Daily summary generated for {symbol}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to generate daily summary for {symbol}: {str(e)}")
        finally:
            db.close()

    def _get_last_signal_type(self, symbol: str) -> Optional[str]:
        """Get the last signal type for a symbol to detect position changes"""
        db = SessionLocal()
        try:
            last_signal = (
                db.query(Signal)
                .filter(Signal.symbol == symbol)
                .order_by(Signal.timestamp.desc())
                .first()
            )
            return last_signal.signal_type if last_signal else None
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

    def restart(self):
        """Restart the scanner with a fresh executor"""
        self.stop()
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.running = True
        logger.info("Scanner restarted with fresh executor")


# Singleton instance
_scanner_service: Optional[ScannerService] = None


def get_scanner(max_workers: int = 10) -> ScannerService:
    """Get or create scanner singleton"""
    global _scanner_service
    if _scanner_service is None:
        _scanner_service = ScannerService(max_workers=max_workers)
    return _scanner_service
