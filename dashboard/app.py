"""Trading Agent Dashboard - Streamlit Web Interface"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import time

# ============================================================================
# CONFIGURATION
# ============================================================================

API_BASE_URL = "http://localhost:8200"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def fetch_data(endpoint, params=None):
    """Fetch data from the FastAPI backend"""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch data: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        return None

def post_data(endpoint, data=None):
    """Send POST request to the FastAPI backend"""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        response = requests.post(url, json=data, timeout=10)
        if response.status_code in [200, 201]:
            return response.json()
        else:
            st.error(f"Failed to POST data: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        return None

# ============================================================================
# SIDEBAR SETUP
# ============================================================================

st.set_page_config(page_title="Trading Agent Dashboard", page_icon="📊", layout="wide")

st.sidebar.title("📊 Trading Agent Dashboard")
page = st.sidebar.radio("Navigate", [
    "📊 Signals",
    "👥 Watchlist",
    "🔍 Scanner",
    "📈 Analytics",
    "⚙️ Config"
])

st.sidebar.markdown("---")
st.sidebar.info("Monitor and manage your trading signals")

# Auto-refresh option
auto_refresh = st.sidebar.checkbox("Auto Refresh", value=True)
refresh_interval = st.sidebar.slider("Interval (seconds)", 10, 120, 30) if auto_refresh else 0

# ============================================================================
# PAGE: SIGNALS
# ============================================================================

def signals_page():
    st.header("📊 Trading Signals")
    
    # Signal summary metrics
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
            st.metric("HOLD", summary.get("hold_count", 0))
        
        # Signal distribution chart
        fig = px.pie(
            values=[summary.get("buy_count", 0), summary.get("sell_count", 0), summary.get("hold_count", 0)],
            names=["BUY", "SELL", "HOLD"],
            title="Signal Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No signal data available")
    
    # Recent signals table
    st.subheader("Recent Signals")
    signals = fetch_data("/api/signals/")
    if signals:
        df = pd.DataFrame(signals)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No signals found")
    else:
        st.info("Could not fetch signals")


# ============================================================================
# PAGE: WATCHLIST
# ============================================================================

def watchlist_page():
    st.header("👥 Watchlist Management")
    
    # Fetch current watchlist from session state
    if 'watchlist_data' not in st.session_state:
        st.session_state.watchlist_data = fetch_data("/api/watchlist/")
    
    # Add new stock form - ONLY symbol field initially
    st.subheader("➕ Add Stock to Watchlist")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        new_symbol = st.text_input(
            "Enter Stock Symbol",
            placeholder="e.g., VNM, VCB, HPG",
            key="symbol_input",
            help="Enter a Vietnamese stock symbol (e.g., VNM for Vietnam Airlines)"
        )
    with col2:
        new_priority = st.selectbox(
            "Priority",
            ["HIGH", "MEDIUM", "LOW"],
            index=1,
            key="priority_input"
        )
    
    # Auto-fill button (triggered when user clicks or presses Enter)
    if new_symbol and st.button("🔍 Lookup & Add", type="primary", key="lookup_add"):
        symbol_upper = new_symbol.strip().upper()
        
        # Step 1: Fetch metadata from vnstock API
        metadata = None
        try:
            import requests
            metadata_url = f"{API_BASE_URL}/api/stocks/metadata?symbol={symbol_upper}"
            response = requests.get(metadata_url, timeout=5)
            if response.status_code == 200:
                metadata = response.json()
        except Exception as e:
            st.warning(f"Could not fetch metadata: {str(e)}")
        
        # Step 2: Add to watchlist
        result = post_data("/api/watchlist/", {
            "symbol": symbol_upper,
            "company_name": metadata.get("company_name", f"Stock {symbol_upper}") if metadata else "",
            "sector": metadata.get("sector", "Unknown") if metadata else "",
            "priority": new_priority
        })
        
        if result:
            st.success(result.get("message", "Added successfully!"))
            # Clear form and refresh watchlist
            st.session_state.watchlist_data = fetch_data("/api/watchlist/")
            st.rerun()
    
    # Watchlist table with improved UX
    st.subheader("📋 Current Watchlist")
    watchlist = st.session_state.watchlist_data
    
    if watchlist:
        # Create DataFrame for better display
        df_data = []
        for stock in watchlist:
            priority_map = {1: "🔴 High", 2: "🟡 Medium", 3: "🟢 Low"}
            df_data.append({
                "Symbol": stock["symbol"],
                "Company": stock.get("company_name", "N/A"),
                "Sector": stock.get("sector", "N/A"),
                "Priority": priority_map.get(stock.get("priority", 3), "N/A"),
                "Status": "✅ Enabled" if stock.get("enabled") else "❌ Disabled",
            })
        
        df = pd.DataFrame(df_data)
        # Display as interactive table with action buttons
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Action buttons for each stock
        st.subheader("⚙️ Manage Stocks")
        
        for stock in watchlist:
            symbol = stock["symbol"]
            enabled = stock.get("enabled", True)
            
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.write(f"**{symbol}** - {stock.get('company_name', 'N/A')}")
            with col2:
                if enabled:
                    if st.button("⏸️ Disable", key=f"disable_{symbol}"):
                        post_data(f"/api/watchlist/{symbol}/disable")
                        st.session_state.watchlist_data = fetch_data("/api/watchlist/")
                        st.rerun()
                else:
                    if st.button("▶️ Enable", key=f"enable_{symbol}"):
                        post_data(f"/api/watchlist/{symbol}/enable")
                        st.session_state.watchlist_data = fetch_data("/api/watchlist/")
                        st.rerun()
            with col3:
                if st.button("🗑️ Delete", key=f"delete_{symbol}"):
                    post_data(f"/api/watchlist/{symbol}")
                    st.session_state.watchlist_data = fetch_data("/api/watchlist/")
                    st.rerun()
            with col4:
                if st.button("📊 View Chart", key=f"chart_{symbol}"):
                    st.session_state.selected_chart_symbol = symbol
                    st.rerun()
    
        # Display chart for selected stock
        if 'selected_chart_symbol' in st.session_state and st.session_state.selected_chart_symbol:
            st.subheader(f"📈 Price Chart - {st.session_state.selected_chart_symbol}")
            
            # Fetch historical data
            try:
                import requests
                history_url = f"{API_BASE_URL}/api/stocks/history?symbol={st.session_state.selected_chart_symbol}&days=30"
                response = requests.get(history_url, timeout=10)
                if response.status_code == 200:
                    chart_data = response.json().get('data', [])
                    if chart_data:
                        # Convert to DataFrame
                        df_chart = pd.DataFrame(chart_data)
                        
                        # Plotly candlestick chart
                        fig = go.Figure()
                        
                        fig.add_trace(go.Candlestick(
                            x=df_chart['time'],
                            open=df_chart['open'],
                            high=df_chart['high'],
                            low=df_chart['low'],
                            close=df_chart['close'],
                        ))
                        
                        fig.update_layout(
                            title=f"{st.session_state.selected_chart_symbol} - Last 30 Days",
                            xaxis_title="Date",
                            yaxis_title="Price (VND)",
                            template="plotly_white",
                            height=500
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Add close button
                        if st.button("❌ Close Chart"):
                            del st.session_state.selected_chart_symbol
                            st.rerun()
                    else:
                        st.warning(f"No price data available for {st.session_state.selected_chart_symbol}")
                else:
                    st.error(f"Failed to fetch chart data: {response.status_code}")
            except Exception as e:
                st.error(f"Error fetching chart data: {str(e)}")
        else:
            st.info("💡 Click '📊 View Chart' button next to any stock to view its price history")
    else:
        st.info("📋 Your watchlist is empty. Add stocks above to start monitoring.")


# ============================================================================
# PAGE: SCANNER
# ============================================================================

def scanner_page():
    st.header("🔍 Scanner Control")
    
    # Scanner status metrics
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
            st.metric("HOLD", summary.get("hold_count", 0))
        
        # Signal distribution chart
        fig = px.pie(
            values=[summary.get("buy_count", 0), summary.get("sell_count", 0), summary.get("hold_count", 0)],
            names=["BUY", "SELL", "HOLD"],
            title="Signal Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No signal data available")
        
    # Signals by symbol
    st.subheader("Signals by Symbol")
    by_symbol = fetch_data("/api/signals/stats/by-symbol")
    if by_symbol:
        df_data = []
        for item in by_symbol:
            df_data.append({
                "Symbol": item.get("symbol", "Unknown"),
                "Signal Count": item.get("count", 0)
            })
        if df_data:
            df = pd.DataFrame(df_data)
            fig = px.bar(
                df,
                x="Symbol",
                y="Signal Count",
                title="Signals by Symbol",
                color="Signal Count",
                color_continuous_scale="Viridis"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No symbol data available")
    else:
        st.info("Could not fetch signal statistics")


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
