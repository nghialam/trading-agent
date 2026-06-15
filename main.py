#!/usr/bin/env python3
"""
Main entry point for the Autonomous Trading Agent
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging(log_level="INFO"):
    """Configure logging"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "trading_agent.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    parser = argparse.ArgumentParser(description="Autonomous Trading Agent")
    parser.add_argument(
        "--symbol", 
        type=str, 
        default="VNM",
        help="Stock symbol to trade (e.g., VNM, FPT)"
    )
    parser.add_argument(
        "--mode", 
        type=str, 
        choices=["backtest", "live"],
        default="backtest",
        help="Trading mode: backtest or live"
    )
    parser.add_argument(
        "--start-date", 
        type=str, 
        default="2024-01-01",
        help="Backtest start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date", 
        type=str, 
        default="2024-12-31",
        help="Backtest end date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--log-level", 
        type=str, 
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info(f"Initializing Trading Agent for {args.symbol}")
    logger.info(f"Mode: {args.mode}")
    
    try:
        # Import here to ensure path is set correctly
        sys.path.insert(0, str(Path(__file__).parent))
        from src.agent import TradingAgent
        
        # Initialize the trading agent
        agent = TradingAgent(symbol=args.symbol)
        
        if args.mode == "backtest":
            logger.info("Starting backtest mode")
            results = agent.backtest(
                start_date=args.start_date,
                end_date=args.end_date
            )
            logger.info(f"Backtest completed. Results: {results}")
        elif args.mode == "live":
            logger.info("Starting live trading mode")
            agent.run_live()
        
    except KeyboardInterrupt:
        logger.info("Agent stopped by user")
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
