"""
Signal Management Routes
REST endpoints for trading signal CRUD operations
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from database.config import get_db
from database.models import Signal, Watchlist
import pandas as pd

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/")
def list_signals(
    symbol: Optional[str] = Query(None, description="Filter by stock symbol"),
    signal_type: Optional[str] = Query(None, description="Filter by type (BUY/SELL/HOLD)"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    min_confidence: Optional[float] = Query(None, description="Minimum confidence score"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    sort_by: str = Query("timestamp", description="Sort by field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    db: Session = Depends(get_db)
):
     """List all signals with optional filters"""
    query = db.query(Signal)
    
     # Apply filters
    if symbol:
        query = query.filter(Signal.symbol == symbol)
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type.upper())
    if start_date:
        query = query.filter(Signal.timestamp >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(Signal.timestamp <= datetime.fromisoformat(end_date))
    if min_confidence is not None:
        query = query.filter(Signal.confidence_score >= min_confidence)
    
     # Sort
    sort_field = getattr(Signal, sort_by, Signal.timestamp)
    if sort_order == "desc":
        query = query.order_by(sort_field.desc())
    else:
        query = query.order_by(sort_field.asc())
    
     # Paginate
    signals = query.offset(offset).limit(limit).all()
    
    return [
         {
             "id": s.id,
             "symbol": s.symbol,
             "timestamp": s.timestamp.isoformat() if s.timestamp else None,
             "signal_type": s.signal_type,
             "confidence_score": s.confidence_score,
             "price_at_signal": s.price_at_signal,
             "indicators": s.indicators,
             "metadata": s.metadata,
             "processed": s.processed,
         }
         for s in signals
     ]


@router.get("/{signal_id}")
def get_signal(signal_id: int, db: Session = Depends(get_db)):
    """Get signal details by ID"""
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    return {
         "id": signal.id,
         "symbol": signal.symbol,
         "timestamp": signal.timestamp.isoformat() if signal.timestamp else None,
         "signal_type": signal.signal_type,
         "confidence_score": signal.confidence_score,
         "price_at_signal": signal.price_at_signal,
         "indicators": signal.indicators,
         "metadata": signal.metadata,
         "processed": signal.processed,
     }


@router.post("/")
def create_signal(
    symbol: str = Query(..., description="Stock symbol"),
    signal_type: str = Query("HOLD", description="Signal type (BUY/SELL/HOLD)"),
    confidence_score: float = Query(0.0, description="Confidence score 0-1"),
    price_at_signal: float = Query(0.0, description="Price at signal time"),
    indicators: dict = Query(None, description="Technical indicator values"),
    db: Session = Depends(get_db)
):
     """Create a new signal (manual trigger)"""
      # Validate symbol exists in watchlist
    stock = db.query(Watchlist).filter(Watchlist.symbol == symbol.upper()).first()
    if not stock or not stock.enabled:
        raise HTTPException(status_code=400, detail=f"Symbol {symbol} not in active watchlist")
    
     # Create signal
    new_signal = Signal(
        symbol=symbol.upper(),
        signal_type=signal_type.upper(),
        confidence_score=confidence_score,
        price_at_signal=price_at_signal,
        indicators=indicators or {},
        metadata={"source": "manual_trigger"}
    )
    db.add(new_signal)
    db.commit()
    db.refresh(new_signal)
    
    return {
         "id": new_signal.id,
         "symbol": new_signal.symbol,
         "signal_type": new_signal.signal_type,
         "confidence_score": new_signal.confidence_score,
         "message": f"Signal created for {symbol}"
     }


@router.delete("/{signal_id}")
def delete_signal(signal_id: int, db: Session = Depends(get_db)):
     """Delete signal by ID"""
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    db.delete(signal)
    db.commit()
    
    return {"message": f"Signal {signal_id} deleted"}


@router.get("/stats/summary")
def signal_summary(db: Session = Depends(get_db)):
     """Get signal statistics summary"""
    from sqlalchemy import func
    
     # Total signals by type
    total = db.query(Signal).count()
    buy_count = db.query(Signal).filter(Signal.signal_type == "BUY").count()
    sell_count = db.query(Signal).filter(Signal.signal_type == "SELL").count()
    hold_count = db.query(Signal).filter(Signal.signal_type == "HOLD").count()
    
     # Average confidence by type
    avg_buy_conf = db.query(func.avg(Signal.confidence_score)).filter(
        Signal.signal_type == "BUY"
    ).scalar() or 0
    
    return {
         "total_signals": total,
         "buy_count": buy_count,
         "sell_count": sell_count,
         "hold_count": hold_count,
         "avg_buy_confidence": round(avg_buy_conf, 4),
     }


@router.get("/stats/by-symbol")
def signal_stats_by_symbol(db: Session = Depends(get_db)):
     """Get signal statistics grouped by symbol"""
    from sqlalchemy import func
    
    stats = (
        db.query(
            Signal.symbol,
            func.count(Signal.id).label("total"),
            func.avg(Signal.confidence_score).label("avg_confidence"),
            func.sum(func.case((Signal.signal_type == "BUY", 1), else_=0)).label("buys"),
            func.sum(func.case((Signal.signal_type == "SELL", 1), else_=0)).label("sells"),
        )
        .group_by(Signal.symbol)
        .all()
    )
    
    return [
         {
             "symbol": s.symbol,
             "total_signals": s.total,
             "avg_confidence": round(float(s.avg_confidence or 0), 4),
             "buy_count": s.buys,
             "sell_count": s.sells,
         }
         for s in stats
     ]
