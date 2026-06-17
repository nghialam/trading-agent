"""Watchlist Management Routes - REST endpoints for stock watchlist CRUD operations"""

from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session
from datetime import datetime
from database.config import get_db
from database.models import Watchlist

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("/")
def list_watchlist(enabled_only: bool = Query(False), db: Session = Depends(get_db)):
    """List all stocks in watchlist"""
    query = db.query(Watchlist)
    if enabled_only:
        query = query.filter(Watchlist.enabled == True)
    stocks = query.all()
    return [{"symbol": s.symbol, "company_name": s.name, "sector": s.sector, "priority": s.priority, "enabled": s.enabled, "added_at": s.created_at.isoformat() if s.created_at else None} for s in stocks]


@router.get("/{symbol}")
def get_watchlist_item(symbol: str, db: Session = Depends(get_db)):
    """Get watchlist item by symbol"""
    stock = db.query(Watchlist).filter(Watchlist.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found in watchlist")
    return {"symbol": stock.symbol, "company_name": stock.name, "sector": stock.sector, "priority": stock.priority, "enabled": stock.enabled, "added_at": stock.created_at.isoformat() if stock.created_at else None}


@router.post("/")
def add_to_watchlist(stock: dict = Body(...), db: Session = Depends(get_db)):
    """Add stock to watchlist"""
    symbol = stock.get("symbol", "").upper()
    name = stock.get("company_name", "")
    sector = stock.get("sector", "")
    priority_str = stock.get("priority", "LOW")
    # Convert priority string to integer
    priority_map = {"LOW": 3, "MEDIUM": 2, "HIGH": 1}
    priority = priority_map.get(priority_str.upper(), 3)
    existing = db.query(Watchlist).filter(Watchlist.symbol == symbol).first()
    if existing:
        raise HTTPException(status_code=400, detail="Stock already in watchlist")
    new_stock = Watchlist(symbol=symbol, name=name, sector=sector, priority=priority, enabled=True)
    db.add(new_stock)
    db.commit()
    return {"message": f"Added {symbol} to watchlist", "symbol": symbol}


@router.put("/{symbol}")
def update_watchlist_item(symbol: str, company_name: str = Query(None), sector: str = Query(None), priority: str = Query(None), db: Session = Depends(get_db)):
    """Update watchlist item"""
    stock = db.query(Watchlist).filter(Watchlist.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    if company_name:
        stock.name = company_name
    if sector:
        stock.sector = sector
    if priority:
         stock.priority = {"LOW": 3, "MEDIUM": 2, "HIGH": 1}.get(priority.upper(), 3)
    db.commit()
    return {"message": f"Updated {symbol}", "symbol": symbol}


@router.delete("/{symbol}")
def remove_from_watchlist(symbol: str, db: Session = Depends(get_db)):
    """Remove stock from watchlist"""
    stock = db.query(Watchlist).filter(Watchlist.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    db.delete(stock)
    db.commit()
    return {"message": f"Removed {symbol} from watchlist"}


@router.post("/{symbol}/enable")
def enable_stock(symbol: str, db: Session = Depends(get_db)):
    """Enable stock in watchlist"""
    stock = db.query(Watchlist).filter(Watchlist.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    stock.enabled = True
    db.commit()
    return {"message": f"Enabled {symbol}", "symbol": symbol, "enabled": True}


@router.post("/{symbol}/disable")
def disable_stock(symbol: str, db: Session = Depends(get_db)):
    """Disable stock in watchlist"""
    stock = db.query(Watchlist).filter(Watchlist.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    stock.enabled = False
    db.commit()
    return {"message": f"Disabled {symbol}", "symbol": symbol, "enabled": False}
