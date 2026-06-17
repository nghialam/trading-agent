"""
Streamlit Web Dashboard for Trading Agent System
Real-time signal monitoring, watchlist management, and analytics
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import time

# Configuration
API_BASE_URL = st.sidebar.selectbox(
    "API Base URL",
    ["http://localhost:8000", "http://127.0.0.1:8000"],
    index=0
)

st.set_page_config(page_title="Trading Agent Dashboard", page_icon="📈", layout="wide")

st.title("📈 Trading Agent Dashboard")
st.markdown("**24/7 Automated Stock Scanning & Signal Management System**")

# Sidebar navigation
st.sidebar.header("Navigation")
page = st.sidebar.radio("", ["📊 Signals", "👥 Watchlist", "🔍 Scanner", "📈 Analytics", "⚙️ Config"])

# Auto-refresh setting
auto_refresh = st.sidebar.checkbox("Auto Refresh (30s)", value=True)
refresh_interval = 30 if auto_refresh else None


def fetch_data(endpoint, params=None):
    """Fetch data from API"""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        response = requests.get(url, params=params or {}, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Connection Error: {str(e)}")
        return None


def post_data(endpoint, data=None):
    """Post data to API"""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        response = requests.post(url, json=data or {}, timeout=10)
        if response.status_code in [200, 201]:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Connection Error: {str(e)}")
        return None


# ============================================================================
# PAGE: SIGNALS
# ============================================================================

def signals_page():
    st.header("📊 Signal Monitoring")
    
     # Filters
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        symbol_filter = st.selectbox("Symbol", ["All"] + list(pd.read_json(f"{API_BASE_URL}/api/watchlist") or []))
    with col2:
        type_filter = st.selectbox("Type", ["All", "BUY", "SELL", "HOLD"])
    with col3:
        date_from = st.date_input("From", datetime.now() - timedelta(days=7))
    with col4:
        date_to = st.date_input("To", datetime.now())
    
      # Fetch signals
    params = {}
    if symbol_filter != "All":
        params["symbol"] = symbol_filter
    if type_filter != "All":
        params["signal_type"] = type_filter
    
    signals = fetch_data("/api/signals/", params)
    
    if signals:
          # Summary cards
         buy_count = sum(1 for s in signals if s.get("signal_type") == "BUY")
        sell_count = sum(1 for s in signals if s.get("signal_type") == "SELL")
        hold_count = sum(1 for s in signals if s.get("signal_type") == "HOLD")
        
         st.metric("Total Signals", len(signals))
        st.metric("BUY", buy_count)
        st.metric("SELL", sell_count)
        st.metric("HOLD", hold_count)
        
          # Signals table
         df = pd.DataFrame(signals)
         if not df.empty:
              df["timestamp"] = pd.to_datetime(df["timestamp"])
             df = df.sort_values("timestamp", ascending=False)
             st.dataframe(df, use_container_width=True)
          else:
             st.info("No signals found")
      else:
         st.warning("Could not fetch signals. Check API connection.")


# ============================================================================
# PAGE: WATCHLIST
# ============================================================================

def watchlist_page():
    st.header("👥 Watchlist Management")
    
     # Fetch current watchlist
    watchlist = fetch_data("/api/watchlist/")
    
      # Add new stock form
    st.subheader("Add Stock to Watchlist")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        new_symbol = st.text_input("Symbol", "VNM")
    with col2:
        new_name = st.text_input("Company Name", "Vietnam Airlines")
    with col3:
        new_sector = st.text_input("Sector", "Aviation")
    with col4:
        new_priority = st.selectbox("Priority", [1, 2, 3], index=1)
    
    if st.button("Add to Watchlist"):
        result = post_data("/api/watchlist/", {
            "symbol": new_symbol.upper(),
            "name": new_name,
            "sector": new_sector,
            "priority": new_priority
         })
        if result:
            st.success(result.get("message", "Added successfully"))
    
      # Watchlist table
    st.subheader("Current Watchlist")
    if watchlist:
          df = pd.DataFrame(watchlist)
          # Enable/disable toggle
         for idx, row in df.iterrows():
              col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
             with col1:
                 st.write(f"**{row['symbol']}** - {row.get('name', 'N/A')}")
             with col2:
                 st.write(f"Sector: {row.get('sector', 'N/A')}")
             with col3:
                 st.write(f"Priority: {row['priority']}")
             with col4:
                  if row['enabled']:
                     if st.button("Disable", key=f"disable_{row['symbol']}"):
                         post_data(f"/api/watchlist/{row['symbol']}/disable")
                         st.rerun()
                  else:
                      if st.button("Enable", key=f"enable_{row['symbol']}"):
                          post_data(f"/api/watchlist/{row['symbol']}/enable")
                          st.rerun()
              
              # Delete button
             if st.button("Delete", key=f"delete_{row['symbol']}"):
                 post_data(f"/api/watchlist/{row['symbol']}")
                 st.rerun()
      else:
         st.info("Watchlist is empty")


# ============================================================================
# PAGE: SCANNER
# ============================================================================

def scanner_page():
    st.header("🔍 Scanner Control")
    
     # Scanner status
    status = fetch_data("/api/scanner/status")
    if status:
          col1, col2, col3, col4 = st.columns(4)
         with col1:
             st.metric("Running", "Yes" if status.get("scanner_running") else "No")
         with col2:
             st.metric("Enabled Stocks", status.get("total_enabled_stocks", 0))
         with col3:
             st.metric("Signals (1h)", status.get("signals_last_hour", 0))
         with col4:
             st.metric("Errors (1h)", status.get("errors_last_hour", 0))
        
          # Control buttons
         st.subheader("Controls")
         col1, col2 = st.columns(2)
         with col1:
              if st.button("Start Scanner", type="primary"):
                  result = post_data("/api/scanner/start")
                  if result:
                      st.success(result.get("message"))
                      st.rerun()
         with col2:
              if st.button("Stop Scanner", type="secondary"):
                  result = post_data("/api/scanner/stop")
                  if result:
                      st.warning(result.get("message"))
                      st.rerun()
      else:
         st.error("Could not fetch scanner status")
    
      # Manual scan
    st.subheader("Manual Scan")
    col1, col2 = st.columns(2)
    with col1:
        scan_symbol = st.text_input("Symbol", "VNM")
    with col2:
         if st.button("Scan Now"):
             result = post_data(f"/api/scanner/scan/{scan_symbol}")
             if result:
                 st.info(result.get("message"))
    
      # Scanner logs
    st.subheader("Scanner Logs")
    log_level = st.selectbox("Log Level", ["All", "INFO", "WARNING", "ERROR"])
    limit = st.slider("Limit", 10, 100, 50)
    
    params = {"limit": limit}
    if log_level != "All":
        params["level"] = log_level
    
    logs = fetch_data("/api/scanner/logs", params)
    if logs:
          df = pd.DataFrame(logs)
         if not df.empty:
             st.dataframe(df, use_container_width=True)
         else:
             st.info("No logs found")


# ============================================================================
# PAGE: ANALYTICS
# ============================================================================

def analytics_page():
    st.header("📈 Analytics Dashboard")
    
      # Signal summary
    summary = fetch_data("/api/signals/stats/summary")
    if summary:
          col1, col2, col3, col4 = st.columns(4)
         with col1:
             st.metric("Total Signals", summary.get("total_signals", 0))
         with col2:
             st.metric("BUY", summary.get("buy_count", 0))
         with col3:
             st.metric("SELL", summary.get("sell_count", 0))
         with col4:
             st.metric("Avg BUY Confidence", f"{summary.get('avg_buy_confidence', 0):.2%}")
        
          # Signal distribution chart
         fig = px.pie(
              values=[summary.get("buy_count", 0), summary.get("sell_count", 0), summary.get("hold_count", 0)],
             names=["BUY", "SELL", "HOLD"],
             title="Signal Distribution"
          )
         st.plotly_chart(fig, use_container_width=True)
      else:
         st.info("No signal data available")
    
      # Stats by symbol
    stats_by_symbol = fetch_data("/api/signals/stats/by-symbol")
    if stats_by_symbol:
          st.subheader("Signals by Symbol")
         df = pd.DataFrame(stats_by_symbol)
         if not df.empty:
              fig2 = px.bar(
                  df,
                  x="symbol",
                  y=["buy_count", "sell_count"],
                  title="Buy/Sell Count by Symbol",
                  labels={"value": "Count", "variable": "Type"}
               )
             st.plotly_chart(fig2, use_container_width=True)
          else:
             st.info("No symbol data available")


# ============================================================================
# PAGE: CONFIG
# ============================================================================

def config_page():
    st.header("⚙️ Configuration")
    
      # Scanner config
    st.subheader("Scanner Configuration")
    config = fetch_data("/api/scanner/config")
    if config:
          for key, value in config.items():
             st.text_input(key.capitalize(), value)
         if st.button("Save Changes"):
             st.success("Configuration saved")
      else:
         st.info("Could not load scanner configuration")


# ============================================================================
# MAIN APP LOGIC
# ============================================================================

if page == "📊 Signals":
    signals_page()
elif page == "👥 Watchlist":
    watchlist_page()
elif page == "🔍 Scanner":
    scanner_page()
elif page == "📈 Analytics":
    analytics_page()
elif page == "⚙️ Config":
    config_page()

# Auto-refresh
if auto_refresh and refresh_interval:
    time.sleep(refresh_interval)
    st.rerun()
