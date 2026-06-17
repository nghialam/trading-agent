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
    symbol = Column(String(20), unique=True, nullable=False, index=True)   # e.g., "VNM", "VCB"
    name = Column(String(100), nullable=True)                                # Company name
    sector = Column(String(50), nullable=True)                               # Sector classification
    priority = Column(Integer, default=1, nullable=False)                   # 1=high (VN30), 2=medium, 3=low
    enabled = Column(Boolean, default=True, nullable=False)                 # Enable/disable monitoring
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
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
    timestamp = Column(DateTime, nullable=False, index=True)                 # Bar timestamp
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    
    # Relationships
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
    signal_type = Column(String(20), nullable=False)                         # BUY, SELL, HOLD
    confidence_score = Column(Float, nullable=False)                         # 0.0 - 1.0
    price_at_signal = Column(Float, nullable=True)                           # Stock price when signal generated
    
    # Technical indicator snapshot (JSON for flexibility)
    indicators = Column(JSON, nullable=True)                                  # RSI, MACD, BB data
    
    # Additional metadata (extensible)
    extra_metadata = Column('metadata', JSON, nullable=True)                   # Custom fields
    
    # Processing status
    processed = Column(Boolean, default=False, nullable=False)               # Mark when processed
    processed_at = Column(DateTime, nullable=True)                            # When processed
    
    # Error tracking
    error_message = Column(String(500), nullable=True)                        # Last error if any
    
    # Relationships
    watchlist = relationship("Watchlist", back_populates="signals")

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
    level = Column(String(10), nullable=False)                                 # INFO, WARNING, ERROR
    component = Column(String(50), nullable=False)                             # scanner, api, dashboard
    message = Column(String(1000), nullable=False)
    details = Column(JSON, nullable=True)                                       # Additional context

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
    key = Column(String(50), unique=True, nullable=False)                     # Config key
    value = Column(String(500), nullable=False)                                # Config value
    description = Column(String(200), nullable=True)                           # Config description
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ScannerConfig(key='{self.key}', value='{self.value}')>"


# Create indexes for common query patterns
def create_indexes():
    """Create additional indexes for performance"""
    from database.config import engine
    Base.metadata.create_all(bind=engine)
    print("Indexes created successfully")
