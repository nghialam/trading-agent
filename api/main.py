"""
FastAPI Backend for Trading Agent System
REST API for signal CRUD, watchlist management, and scanner control
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.config import engine
from database.models import Base


# Global scanner service reference
_scanner_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    # Startup
    from services.scanner import get_scanner
    global _scanner_service
    _scanner_service = get_scanner()
    yield
    # Shutdown
    if _scanner_service:
        _scanner_service.stop()


app = FastAPI(
    title="Trading Agent API",
    description="REST API for 24/7 automated stock scanning and signal management",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "trading-agent-api",
        "version": "2.0.0"
    }


@app.get("/")
def root():
    """Root endpoint with API info"""
    return {
        "message": "Trading Agent API v2.0",
        "docs": "/docs",
        "endpoints": {
            "signals": "/api/signals",
            "watchlist": "/api/watchlist",
            "scanner": "/api/scanner"
        }
    }


# Import routes after app is defined
from api.routes import signals, watchlist, scanner  # noqa: E402

app.include_router(signals.router, prefix="/api")
app.include_router(watchlist.router, prefix="/api")
app.include_router(scanner.router, prefix="/api")
