# Daily Maintenance Checklist

- [ ] Check scanner status: `curl http://localhost:8200/api/scanner/status`
- [ ] Verify scanner is running: `"scanner_running": true`
- [ ] Check signal count is increasing: `"signals_last_hour" > 0`
- [ ] Monitor error count: `"errors_last_hour" == 0`
- [ ] Review system logs: `curl 'http://localhost:8200/api/scanner/logs?limit=10'`
- [ ] Verify database connectivity: Check PostgreSQL is responding

# Weekly Maintenance Checklist

- [ ] Review all watchlist stocks are enabled and valid
- [ ] Check signal quality - review HOLD/BUY/SELL distribution
- [ ] Verify scanner config is optimal (scan_interval, priority intervals)
- [ ] Review system logs for recurring errors or warnings
- [ ] Check disk space usage for PostgreSQL and application logs
- [ ] Validate data freshness from vnstock API

# Monthly Maintenance Checklist

- [ ] Review and update watchlist with current market conditions
- [ ] Analyze signal performance over the month
- [ ] Check Python dependencies for security updates
- [ ] Review and rotate log files if needed
- [ ] Test backup and restore procedures for PostgreSQL
- [ ] Verify all services start correctly after restart
