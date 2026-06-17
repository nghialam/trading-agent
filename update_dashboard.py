#!/usr/bin/env python3
"""Helper script to update dashboard/app.py with improved watchlist_page."""

with open('dashboard/app.py', 'r') as f:
    content = f.read()

# Find the start and end markers
start_marker = "# ============================================================================\n# PAGE: WATCHLIST\n# ============================================================================\n"
end_marker = "\n\n# ============================================================================\n# MAIN APP LOGIC\n# ============================================================================\n"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx != -1 and end_idx != -1:
    new_content = """# ============================================================================
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
                st.button("📊 View Chart", key=f"chart_{symbol}")
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


""" + content[end_idx:]

    with open('dashboard/app.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Successfully updated dashboard/app.py")
else:
    print(f"❌ Could not find markers. start_idx={start_idx}, end_idx={end_idx}")
