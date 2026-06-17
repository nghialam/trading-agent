"""Signal Management Routes - REST endpoints for trading signal CRUD operations"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from database.config import get_db
from database.models import Signal, Watchlist

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/")
def list_signals(
    symbol: Optional[str] = Query(None),
    signal_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    min_confidence: Optional[float] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("timestamp"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db)
):
    """List all signals with optional filters"""
    query = db.query(Signal)
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
    sort_field = getattr(Signal, sort_by, Signal.timestamp)
    if sort_order == "desc":
        query = query.order_by(sort_field.desc())
    else:
        query = query.order_by(sort_field.asc())
    signals_list = query.offset(offset).limit(limit).all()
    return [{"id": s.id, "symbol": s.symbol, "timestamp": s.timestamp.isoformat() if s.timestamp else None, "signal_type": s.signal_type, "confidence_score": s.confidence_score, "price_at_signal": s.price_at_signal, "indicators": s.indicators, "extra_metadata": s.extra_metadata, "processed": s.processed} for s in signals_list]


@router.get("/{signal_id}")
def get_signal(signal_id: int, db: Session = Depends(get_db)):
    """Get signal details by ID"""
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return {"id": signal.id, "symbol": signal.symbol, "timestamp": signal.timestamp.isoformat() if signal.timestamp else None, "signal_type": signal.signal_type, "confidence_score": signal.confidence_score, "price_at_signal": signal.price_at_signal, "indicators": signal.indicators, "extra_metadata": signal.extra_metadata, "processed": signal.processed}


@router.post("/")
def create_signal(signal: dict, db: Session = Depends(get_db)):
    """Create a new signal (manual entry)"""
    new_signal = Signal(
        symbol=signal["symbol"],
        timestamp=datetime.fromisoformat(signal["timestamp"]) if isinstance(signal.get("timestamp"), str) else datetime.utcnow(),
        signal_type=signal["signal_type"],
        confidence_score=signal.get("confidence_score", 0.0),
        price_at_signal=signal.get("price_at_signal", 0.0),
        indicators=signal.get("indicators", {}),
        extra_metadata=signal.get("extra_metadata", {})
    )
    db.add(new_signal)
    db.commit()
    db.refresh(new_signal)
    return {"id": new_signal.id, "symbol": new_signal.symbol, "timestamp": new_signal.timestamp.isoformat(), "signal_type": new_signal.signal_type, "confidence_score": new_signal.confidence_score}


@router.delete("/{signal_id}")
def delete_signal(signal_id: int, db: Session = Depends(get_db)):
    """Delete a signal by ID"""
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    db.delete(signal)
    db.commit()
    return {"message": f"Signal {signal_id} deleted"}


@router.get("/stats/summary")
def get_signal_summary(db: Session = Depends(get_db)):
    """Get signal statistics summary"""
    total = db.query(Signal).count()
    buy_count = db.query(Signal).filter(Signal.signal_type == "BUY").count()
    sell_count = db.query(Signal).filter(Signal.signal_type == "SELL").count()
    hold_count = db.query(Signal).filter(Signal.signal_type == "HOLD").count()
    return {"total_signals": total, "buy_count": buy_count, "sell_count": sell_count, "hold_count": hold_count}


@router.get("/stats/by-symbol")
def get_signal_by_symbol(symbol: str = Query(...), db: Session = Depends(get_db)):
    """Get signal statistics by symbol"""
    signals = db.query(Signal).filter(Signal.symbol == symbol.upper()).all()
    if not signals:
        return {"symbol": symbol.upper(), "count": 0}
    buy_count = sum(1 for s in signals if s.signal_type == "BUY")
    sell_count = sum(1 for s in signals if s.signal_type == "SELL")
    hold_count = sum(1 for s in signals if s.signal_type == "HOLD")
    avg_confidence = sum(s.confidence_score for s in signals) / len(signals)
    return {"symbol": symbol.upper(), "count": len(signals), "buy_count": buy_count, "sell_count": sell_count, "hold_count": hold_count, "avg_confidence": round(avg_confidence, 4)}
