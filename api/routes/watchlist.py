"""
Watchlist Management Routes
REST endpoints for adding, removing, and modifying stocks in the watchlist
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from database.config import get_db
from database.models import Watchlist

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("/")
def list_watchlist(
    enabled_only: bool = Query(True, description="Show only enabled stocks"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    priority: Optional[int] = Query(None, description="Filter by priority (1-3)"),
    db: Session = Depends(get_db)
):
     """List all watchlist stocks"""
    query = db.query(Watchlist)
    
    if enabled_only:
        query = query.filter(Watchlist.enabled == True)
    if sector:
        query = query.filter(Watchlist.sector.ilike(f"%{sector}%"))
    if priority is not None:
        query = query.filter(Watchlist.priority == priority)
    
    stocks = query.order_by(Watchlist.priority, Watchlist.symbol).all()
    
    return [
          {
              "id": s.id,
              "symbol": s.symbol,
              "name": s.name,
              "sector": s.sector,
              "priority": s.priority,
              "enabled": s.enabled,
              "created_at": s.created_at.isoformat() if s.created_at else None,
              "updated_at": s.updated_at.isoformat() if s.updated_at else None,
          }
         for s in stocks
      ]


@router.get("/{symbol}")
def get_watchlist_item(symbol: str, db: Session = Depends(get_db)):
     """Get watchlist item by symbol"""
    stock = db.query(Watchlist).filter(Watchlist.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    
    return {
          "id": stock.id,
          "symbol": stock.symbol,
          "name": stock.name,
          "sector": stock.sector,
          "priority": stock.priority,
          "enabled": stock.enabled,
      }


@router.post("/")
def add_to_watchlist(
    symbol: str = Query(..., description="Stock ticker symbol"),
    name: str = Query("", description="Company name"),
    sector: str = Query("", description="Industry sector"),
    priority: int = Query(2, ge=1, le=3, description="Priority (1=high, 2=medium, 3=low)"),
    enabled: bool = Query(True, description="Enable immediately"),
    db: Session = Depends(get_db)
):
      """Add stock to watchlist"""
     symbol = symbol.upper()
      
      # Check if already exists
    existing = db.query(Watchlist).filter(Watchlist.symbol == symbol).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Symbol {symbol} already exists")
    
       # Create new watchlist entry
    new_stock = Watchlist(
        symbol=symbol,
        name=name or symbol,
        sector=sector,
        priority=priority,
        enabled=enabled
     )
    db.add(new_stock)
    db.commit()
    db.refresh(new_stock)
    
    return {
          "id": new_stock.id,
          "symbol": new_stock.symbol,
          "name": new_stock.name,
          "sector": new_stock.sector,
          "priority": new_stock.priority,
          "enabled": new_stock.enabled,
          "message": f"Added {symbol} to watchlist"
      }


@router.put("/{symbol}")
def update_watchlist_item(
    symbol: str,
    name: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    priority: Optional[int] = Query(None, ge=1, le=3),
    enabled: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
      """Update stock configuration"""
    stock = db.query(Watchlist).filter(Watchlist.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    
       # Update fields
    if name is not None:
        stock.name = name
    if sector is not None:
        stock.sector = sector
    if priority is not None:
        stock.priority = priority
    if enabled is not None:
        stock.enabled = enabled
    
    stock.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(stock)
    
    return {
          "id": stock.id,
          "symbol": stock.symbol,
          "name": stock.name,
          "sector": stock.sector,
          "priority": stock.priority,
          "enabled": stock.enabled,
          "message": f"Updated {symbol}"
      }


@router.delete("/{symbol}")
def remove_from_watchlist(symbol: str, db: Session = Depends(get_db)):
      """Remove stock from watchlist"""
    stock = db.query(Watchlist).filter(Watchlist.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    
    db.delete(stock)
    db.commit()
    
    return {"message": f"Removed {symbol} from watchlist"}


@router.post("/{symbol}/enable")
def enable_stock(symbol: str, db: Session = Depends(get_db)):
      """Enable stock in watchlist"""
    stock = db.query(Watchlist).filter(Watchlist.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    
    stock.enabled = True
    db.commit()
    
    return {"message": f"Enabled {symbol}", "enabled": True}


@router.post("/{symbol}/disable")
def disable_stock(symbol: str, db: Session = Depends(get_db)):
      """Disable stock in watchlist"""
    stock = db.query(Watchlist).filter(Watchlist.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    
    stock.enabled = False
    db.commit()
    
    return {"message": f"Disabled {symbol}", "enabled": False}
