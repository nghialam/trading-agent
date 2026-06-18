"""Scanner Control Routes - REST endpoints for controlling the 24/7 scanner service"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from database.config import get_db
from database.models import ScannerConfig, SystemLog, Watchlist, Signal
import threading

router = APIRouter(prefix="/scanner", tags=["scanner"])

# Track scanner state
_scanner_thread: threading.Thread = None
_scanner_running = False


@router.get("/status")
def get_scanner_status(db: Session = Depends(get_db)):
    """Get scanner service status and statistics"""
    global _scanner_running
    total_stocks = db.query(Watchlist).filter(Watchlist.enabled == True).count()
    
    # Calculate one hour ago properly
    now = datetime.utcnow()
    one_hour_ago = now.replace(minute=0, second=0, microsecond=0)
    
    recent_signals = db.query(Signal).filter(Signal.timestamp >= one_hour_ago).count()
    recent_errors = db.query(SystemLog).filter(SystemLog.level == "ERROR").filter(SystemLog.timestamp >= one_hour_ago).count()
    
    return {
        "scanner_running": _scanner_running,
        "total_enabled_stocks": total_stocks,
        "signals_last_hour": recent_signals,
        "errors_last_hour": recent_errors,
        "last_scan_time": None
    }


@router.post("/start")
def start_scanning(db: Session = Depends(get_db)):
    """Start scanner service"""
    global _scanner_running
    if _scanner_running:
        return {"message": "Scanner already running", "scanner_running": True}
    
    from services.scanner import get_scanner
    scanner = get_scanner()
    
    # Start scanner in background thread
    def run_scanner():
        global _scanner_running
        try:
            scanner.run()
        finally:
            _scanner_running = False
    
    thread = threading.Thread(target=run_scanner, daemon=True)
    thread.start()
    _scanner_running = True
    
    return {"message": "Scanner service started", "scanner_running": True}


@router.post("/stop")
def stop_scanning(db: Session = Depends(get_db)):
    """Stop scanner service"""
    global _scanner_running
    if not _scanner_running:
        return {"message": "Scanner already stopped", "scanner_running": False}
    
    from services.scanner import get_scanner
    scanner = get_scanner()
    scanner.stop()
    _scanner_running = False
    
    return {"message": "Scanner service stopped", "scanner_running": False}


@router.post("/restart")
def restart_scanning(db: Session = Depends(get_db)):
    """Restart scanner service with fresh executor"""
    global _scanner_running
    if _scanner_running:
        stop_scanning(db)
    
    from services.scanner import get_scanner
    scanner = get_scanner()
    scanner.restart()
    _scanner_running = True
    
    return {"message": "Scanner service restarted", "scanner_running": True}


@router.post("/scan/{symbol}")
def scan_single_stock(symbol: str, db: Session = Depends(get_db)):
    """Manually trigger a scan for a single stock"""
    symbol = symbol.upper()
    stock = db.query(Watchlist).filter(Watchlist.symbol == symbol).first()
    if not stock or not stock.enabled:
        raise HTTPException(status_code=400, detail=f"Stock {symbol} not enabled")
    
    log_entry = SystemLog(
        level="INFO",
        component="scanner_api",
        message=f"Manual scan triggered for {symbol}",
        details={"triggered_by": "api"}
    )
    db.add(log_entry)
    db.commit()
    
    return {"message": f"Scan triggered for {symbol}", "symbol": symbol, "status": "scanning"}


@router.get("/config")
def get_scanner_config(db: Session = Depends(get_db)):
    """Get scanner configuration"""
    configs = {}
    for config in db.query(ScannerConfig).all():
        configs[config.key] = config.value
    return {
        "scan_interval": configs.get("scan_interval", "30"),
        "high_priority_interval": configs.get("high_priority_interval", "10"),
        "low_priority_interval": configs.get("low_priority_interval", "60"),
        "max_workers": configs.get("max_workers", "10")
    }


@router.put("/config")
def update_scanner_config(key: str = Query(...), value: str = Query(...), db: Session = Depends(get_db)):
    """Update scanner configuration"""
    config = db.query(ScannerConfig).filter(ScannerConfig.key == key).first()
    if config:
        config.value = value
        config.updated_at = datetime.utcnow()
    else:
        config = ScannerConfig(key=key, value=value)
        db.add(config)
    db.commit()
    return {"message": f"Updated config {key}", "key": key, "value": value}


@router.get("/logs")
def get_scanner_logs(level: str = Query(None), component: str = Query(None), limit: int = Query(100, ge=1, le=1000), db: Session = Depends(get_db)):
    """Get scanner activity logs"""
    query = db.query(SystemLog)
    if level:
        query = query.filter(SystemLog.level == level.upper())
    if component:
        query = query.filter(SystemLog.component.ilike(f"%{component}%"))
    logs = query.order_by(SystemLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "level": log.level,
            "component": log.component,
            "message": log.message,
            "details": log.details
        }
        for log in logs
    ]
