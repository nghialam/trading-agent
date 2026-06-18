"""
Curated Signals API - REST endpoints for LLM-analyzed signals and daily summaries
Provides curated list of position changes and trading insights
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timedelta
from typing import Optional

from database.config import get_db
from database.models import SignalReview, DailySummary, Signal, Watchlist

router = APIRouter()


@router.get("/curated-signals")
def get_curated_signals(
    db: Session = Depends(get_db),
    symbol: Optional[str] = Query(None, description="Filter by stock symbol"),
    verdict: Optional[str] = Query(None, description="Filter by LLM verdict (QUALIFIED, WEAK, FAKE)"),
    is_position_change: Optional[bool] = Query(None, description="Filter position changes only"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    Get curated signals with LLM analysis.
    
    Returns signals that have been analyzed by LLM, focusing on 
    position changes (HOLD -> BUY/SELL) and qualified signals.
    """
    query = db.query(SignalReview)
    
    # Apply filters
    if symbol:
        query = query.filter(SignalReview.symbol == symbol.upper())
    if verdict:
        query = query.filter(SignalReview.llm_verdict == verdict.upper())
    if is_position_change is not None:
        query = query.filter(SignalReview.is_position_change == is_position_change)
    
    # Order by timestamp descending
    reviews = (
        query.order_by(desc(SignalReview.timestamp))
            .offset(offset)
            .limit(limit)
            .all()
    )
    
    # Build response
    result = []
    for review in reviews:
        result.append({
            'id': review.id,
            'symbol': review.symbol,
            'timestamp': review.timestamp.isoformat(),
            'previous_signal': review.previous_signal,
            'current_signal': review.current_signal,
            'is_position_change': review.is_position_change,
            'llm_verdict': review.llm_verdict,
            'llm_confidence': review.llm_confidence,
            'analysis_notes': review.analysis_notes,
            'llm_analysis': review.llm_analysis
        })
    
    return {
        'total': len(result),
        'limit': limit,
        'offset': offset,
        'signals': result
    }


@router.get("/curated-signals/position-changes")
def get_position_changes(
    db: Session = Depends(get_db),
    symbol: Optional[str] = Query(None, description="Filter by stock symbol"),
    limit: int = Query(10, ge=1, le=50, description="Number of results")
):
    """
    Get only signals where position changed (HOLD -> BUY/SELL).
    
    This is the most curated list - signals that represent actual
    trading opportunities based on LLM verification.
    """
    query = db.query(SignalReview).filter(
        SignalReview.is_position_change == True
    )
    
    if symbol:
        query = query.filter(SignalReview.symbol == symbol.upper())
    
    reviews = (
        query.order_by(desc(SignalReview.timestamp))
            .limit(limit)
            .all()
    )
    
    result = []
    for review in reviews:
        result.append({
            'id': review.id,
            'symbol': review.symbol,
            'timestamp': review.timestamp.isoformat(),
            'previous_signal': review.previous_signal,
            'current_signal': review.current_signal,
            'llm_verdict': review.llm_verdict,
            'llm_confidence': review.llm_confidence,
            'analysis_notes': review.analysis_notes
        })
    
    return {
        'total': len(result),
        'changes': result
    }


@router.get("/daily-summary")
def get_daily_summary(
    db: Session = Depends(get_db),
    symbol: Optional[str] = Query(None, description="Filter by stock symbol"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(10, ge=1, le=100, description="Number of results")
):
    """
    Get daily trading summaries with notable events.
    
    Summarizes what happened during each trading day and provides
    insights for future trading decisions.
    """
    query = db.query(DailySummary)
    
    if symbol:
        query = query.filter(DailySummary.symbol == symbol.upper())
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(DailySummary.date >= from_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d")
            query = query.filter(DailySummary.date <= to_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")
    
    summaries = (
        query.order_by(desc(DailySummary.date))
            .limit(limit)
            .all()
    )
    
    result = []
    for summary in summaries:
        result.append({
            'id': summary.id,
            'symbol': summary.symbol,
            'date': summary.date.isoformat(),
            'summary_text': summary.summary_text,
            'notable_events': summary.notable_events,
            'trading_notes': summary.trading_notes,
            'market_conditions': summary.market_conditions,
            'volume_analysis': summary.volume_analysis
        })
    
    return {
        'total': len(result),
        'limit': limit,
        'summaries': result
    }


@router.get("/daily-summary/market-overview")
def get_market_overview(
    db: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=30, description="Number of days to look back")
):
    """
    Get market-wide overview for recent trading days.
    
    Aggregates summaries across all stocks to provide a 
    high-level view of market conditions.
    """
    # Get today's date
    today = datetime.utcnow().date()
    from_date = today - timedelta(days=days)
    
    # Query market-wide summaries (symbol is None)
    summaries = (
        db.query(DailySummary)
            .filter(DailySummary.symbol == None)
            .filter(DailySummary.date >= from_date)
            .order_by(desc(DailySummary.date))
            .all()
    )
    
    # Also get per-stock summaries for key stocks
    top_stocks = (
        db.query(Watchlist)
            .filter(Watchlist.enabled == True)
            .limit(5)
            .all()
    )
    
    stock_summaries = []
    for stock in top_stocks:
        latest = (
            db.query(DailySummary)
                .filter(DailySummary.symbol == stock.symbol)
                .order_by(desc(DailySummary.date))
                .first()
        )
        if latest:
            stock_summaries.append({
                'symbol': stock.symbol,
                'name': stock.name,
                'summary_text': latest.summary_text,
                'notable_events': latest.notable_events,
                'trading_notes': latest.trading_notes
            })
    
    return {
        'period_days': days,
        'market_wide': [s.summary_text for s in summaries],
        'top_stocks': stock_summaries
    }
