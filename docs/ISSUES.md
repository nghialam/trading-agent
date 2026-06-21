# Issues Found and Fixes Applied

## Critical Issues (Preventing Signal Generation)

### 1. IndentationError in api/routes/scanner.py
- **Symptom**: API cannot start due to `IndentationError: unindent does not match any outer indentation level` at line 67
- **Root Cause**: 
  - Inside `start_scanning()`: `thread = threading.Thread(...)` is not properly indented
  - Duplicate `set_scanner_running` function definitions inside `start_scanning()`, `stop_scanning()`, and `restart_scanning()`
- **Fix**: Rewrite the entire file with proper structure

### 2. _evaluate_rsi_macd() Bug in src/strategy.py
- **Symptom**: SignalGenerator never generates signals
- **Root Cause**: Line 124-125 references `buy_signals` variable but it's not in scope
- **Fix**: The function references undefined `buy_signals` variable

### 3. Signal Generation Logic in services/scanner.py
- **Symptom**: Signals not being generated even when indicators match
- **Root Cause**: 
  - LLM verdict defaults to `{'verdict': 'WEAK', 'confidence': 0.5}` which halves confidence
  - No fallback when vnstock API fails (returns empty data)
  - `_get_last_signal_type()` method is defined twice

### 4. Scanner Service in services/scanner.py
- **Symptom**: Scanner may crash on data fetch
- **Root Cause**: Missing fallback data handling

## Secondary Issues

### 5. Database Configuration
- PostgreSQL is running but `scanner_config` table is empty
- Default scan interval is 30 seconds

### 6. Missing vnstock Package
- Scanner depends on `vnstock` package which may not be installed
- Need to verify package availability

### 7. Duplicate Methods
- `_get_last_signal_type()` defined twice in scanner.py
