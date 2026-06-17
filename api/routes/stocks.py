"""Stock Metadata Routes - REST endpoints for fetching stock info from vnstock"""

from fastapi import APIRouter, Query, HTTPException

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/metadata")
def get_stock_metadata(symbol: str = Query(..., description="Stock symbol to lookup")):
    """Fetch stock metadata (company name, sector) from vnstock API"""
    try:
        from vnstock import Quote
        quote = Quote(source="VCI", symbol=symbol.upper())
        
         # Fetch latest price data to verify symbol exists
        from datetime import datetime, timedelta
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)
        
        df = quote.history(
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval="1D"
         )
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol.upper()} not found")
        
         # Return metadata (vnstock doesn't provide company name/sector, so we return placeholder)
        return {
             "symbol": symbol.upper(),
             "company_name": f"Stock {symbol.upper()}",  # Placeholder - vnstock doesn't provide this
             "sector": "Unknown",  # Placeholder - vnstock doesn't provide this
             "verified": True
         }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch metadata: {str(e)}")
