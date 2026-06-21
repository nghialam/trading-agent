"""Scanner Control Routes - REST endpoints for controlling the 24/7 scanner service"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from database.config import get_db
from database.models import ScannerConfig, SystemLog, Watchlist, Signal
import threading
import time

router = APIRouter(prefix="/scanner", tags=["scanner"])

# Track scanner state and instance
_scanner_thread: threading.Thread = None
_scanner_instance = None
_scanner_running = False


def set_scanner_running(status: bool):
    """Helper to set scanner running status from external code"""
    global _scanner_running
    _scanner_running = status


@router.get("/status")
def get_scanner_status(db: Session = Depends(get_db)):
    """Get scanner service status and statistics"""
    global _scanner_running
    total_stocks = db.query(Watchlist).filter(Watchlist.enabled == True).count()
    
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    
    recent_signals = db.query(Signal).filter(Signal.timestamp >= one_hour_ago).count()
    recent_errors = db.query(SystemLog).filter(
        SystemLog.level == "ERROR"
    ).filter(SystemLog.timestamp >= one_hour_ago).count()
    
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
    global _scanner_running, _scanner_thread, _scanner_instance
    if _scanner_running:
        return {"message": "Scanner already running", "scanner_running": True}
    
    from services.scanner import ScannerService
    _scanner_instance = ScannerService(max_workers=10)
    
    def run_scanner():
        global _scanner_running
        try:
            _scanner_instance.run()
        finally:
            _scanner_running = False

    _scanner_thread = threading.Thread(target=run_scanner, daemon=True)
    _scanner_thread.start()
    _scanner_running = True
    
    return {"message": "Scanner service started", "scanner_running": True}


@router.post("/stop")
def stop_scanning(db: Session = Depends(get_db)):
    """Stop scanner service"""
    global _scanner_running, _scanner_instance
    if not _scanner_running:
        return {"message": "Scanner already stopped", "scanner_running": False}
    
    if _scanner_instance:
        _scanner_instance.stop()
    _scanner_running = False

    return {"message": "Scanner service stopped", "scanner_running": False}


@router.post("/restart")
def restart_scanning(db: Session = Depends(get_db)):
    """Restart scanner service with fresh executor"""
    global _scanner_running, _scanner_thread, _scanner_instance
    if _scanner_running:
        stop_scanning(db)
        time.sleep(1)  # Wait for shutdown
    
    # Create completely new ScannerService instance
    from services.scanner import ScannerService
    _scanner_instance = ScannerService(max_workers=10)
    
    def run_scanner():
        global _scanner_running
        try:
            _scanner_instance.run()
        finally:
            _scanner_running = False

    _scanner_thread = threading.Thread(target=run_scanner, daemon=True)
    _scanner_thread.start()
    _scanner_running = True
    
    return {"message": "Scanner service restarted", "scanner_running": True}


@router.post("/scan/{symbol}")
def scan_single_stock(symbol: str, db: Session = Depends(get_db)):
    """Manually trigger a scan for a single stock"""
    symbol = symbol.upper()
    stock = db.query(Watchlist).filter(
        Watchlist.symbol == symbol,
        Watchlist.enabled == True
    ).first()
    if not stock:
        raise HTTPException(
            status_code=404,
            detail=f"Stock {symbol} not found or disabled"
        )
    
    log_entry = SystemLog(
        level="INFO",
        component="scanner_api",
        message=f"Manual scan triggered for {symbol}",
        details={"symbol": symbol, "triggered_by": "api"}
    )
    db.add(log_entry)
    db.commit()
    
    from services.scanner import ScannerService
    scanner = ScannerService(max_workers=10)
    scanner.scan_single_stock(symbol)
    
    return {"message": f"Scan triggered for {symbol}", "symbol": symbol}


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
