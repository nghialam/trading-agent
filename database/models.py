"""
Database Models
SQLAlchemy models for PostgreSQL database
Normalized schema for scalable signal storage
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from database.config import Base


class Watchlist(Base):
    """
    Stock watchlist configuration
    Defines which stocks to monitor
    """
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=True)
    sector = Column(String(50), nullable=True)
    priority = Column(Integer, default=1, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    signals = relationship("Signal", back_populates="watchlist", cascade="all, delete-orphan")
    price_data = relationship("PriceData", back_populates="watchlist", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_watchlist_symbol', 'symbol'),
        Index('idx_watchlist_enabled', 'enabled'),
    )

    def __repr__(self):
        return f"<Watchlist(symbol='{self.symbol}', priority={self.priority})>"


class PriceData(Base):
    """
    Historical price data (OHLCV)
    Stores raw market data for each stock
    """
    __tablename__ = "price_data"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), ForeignKey("watchlist.symbol"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    
    watchlist = relationship("Watchlist", back_populates="price_data")

    __table_args__ = (
        Index('idx_price_symbol_time', 'symbol', 'timestamp'),
        Index('idx_price_timestamp', 'timestamp'),
    )

    def __repr__(self):
        return f"<PriceData(symbol='{self.symbol}', timestamp='{self.timestamp}')>"


class Signal(Base):
    """
    Trading signals with full metadata
    Normalized schema for extensibility
    """
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), ForeignKey("watchlist.symbol"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    signal_type = Column(String(20), nullable=False)
    confidence_score = Column(Float, nullable=False)
    price_at_signal = Column(Float, nullable=True)
    
    indicators = Column(JSON, nullable=True)
    
    extra_metadata = Column('extra_meta', JSON, nullable=True)
    
    processed = Column(Boolean, default=False, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    
    error_message = Column(String(500), nullable=True)
    
    watchlist = relationship("Watchlist", back_populates="signals")
    review = relationship("SignalReview", back_populates="signal")

    __table_args__ = (
        Index('idx_signal_symbol_time', 'symbol', 'timestamp'),
        Index('idx_signal_type', 'signal_type'),
        Index('idx_signal_confidence', 'confidence_score'),
        Index('idx_signal_processed', 'processed'),
    )

    def __repr__(self):
        return f"<Signal(symbol='{self.symbol}', type='{self.signal_type}', confidence={self.confidence_score})>"


class SystemLog(Base):
    """
    System activity log
    Tracks scanner operations, errors, and health
    """
    __tablename__ = "system_log"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    level = Column(String(10), nullable=False)
    component = Column(String(50), nullable=False)
    message = Column(String(1000), nullable=False)
    details = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_log_timestamp', 'timestamp'),
        Index('idx_log_level', 'level'),
        Index('idx_log_component', 'component'),
    )

    def __repr__(self):
        return f"<SystemLog(level='{self.level}', component='{self.component}', message='{self.message}')>"


class ScannerConfig(Base):
    """
    Scanner configuration settings
    Stores runtime parameters
    """
    __tablename__ = "scanner_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, nullable=False)
    value = Column(String(500), nullable=False)
    description = Column(String(200), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ScannerConfig(key='{self.key}', value='{self.value}')>"


class SignalReview(Base):
    """
    Curated signal reviews with LLM analysis
    Tracks position changes and validates signals
    """
    __tablename__ = "signal_reviews"

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    previous_signal = Column(String(20), nullable=True)
    current_signal = Column(String(20), nullable=False)
    is_position_change = Column(Boolean, default=False, nullable=False)
    
    llm_analysis = Column(JSON, nullable=True)
    llm_verdict = Column(String(20), nullable=True)
    llm_confidence = Column(Float, nullable=True)
    analysis_notes = Column(String(2000), nullable=True)
    
    signal = relationship("Signal", back_populates="review")

    __table_args__ = (
        Index('idx_review_symbol_time', 'symbol', 'timestamp'),
        Index('idx_review_verdict', 'llm_verdict'),
        Index('idx_review_position_change', 'is_position_change'),
    )

    def __repr__(self):
        return f"<SignalReview(symbol='{self.symbol}', verdict='{self.llm_verdict}', change={self.is_position_change})>"


class DailySummary(Base):
    """
    Daily trading summary and notes
    Captures notable events and lessons for future reference
    """
    __tablename__ = "daily_summaries"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, unique=True, nullable=False, index=True)
    symbol = Column(String(20), nullable=True, index=True)
    
    summary_text = Column(String(5000), nullable=True)
    notable_events = Column(JSON, nullable=True)
    trading_notes = Column(String(3000), nullable=True)
    
    market_conditions = Column(JSON, nullable=True)
    volume_analysis = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_summary_date', 'date'),
        Index('idx_summary_symbol', 'symbol'),
    )

    def __repr__(self):
        return f"<DailySummary(date='{self.date}', symbol='{self.symbol}')>"


class PocketPivotData(Base):
    """
    Pocket Pivot indicator data (1h timeframe)
    Tracks pivot points for position determination
    """
    __tablename__ = "pocket_pivot_data"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    pivot_type = Column(String(20), nullable=True)
    pivot_price = Column(Float, nullable=True)
    volume_ratio = Column(Float, nullable=True)
    is_valid = Column(Boolean, default=False, nullable=False)
    
    previous_high = Column(Float, nullable=True)
    previous_low = Column(Float, nullable=True)
    context_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_pivot_symbol_time', 'symbol', 'timestamp'),
        Index('idx_pivot_valid', 'is_valid'),
        Index('idx_pivot_type', 'pivot_type'),
    )

    def __repr__(self):
        return f"<PocketPivotData(symbol='{self.symbol}', type='{self.pivot_type}')>"


def create_indexes():
    """Create additional indexes for performance"""
    from database.config import engine
    Base.metadata.create_all(bind=engine)
    print("Indexes created successfully")
