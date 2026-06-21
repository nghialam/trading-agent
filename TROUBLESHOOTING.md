# Trading Agent System - Troubleshooting Runbook

## Common Issues & Solutions

### Issue 1: Scanner Not Generating Signals
**Symptoms**: `signals_last_hour` is 0, scanner shows `"scanner_running": false`
**Steps**:
1. Check scanner status: `curl http://localhost:8200/api/scanner/status`
2. Start scanner: `curl -X POST http://localhost:8200/api/scanner/start`
3. Check system logs: `curl 'http://localhost:8200/api/scanner/logs?limit=20'`
4. Verify PostgreSQL is running: `psql -U trading_user -d trading_agent -c "SELECT count(*) FROM signals;"`

### Issue 2: Database Connection Failed
**Symptoms**: API returns 500 errors, connection timeout messages
**Steps**:
1. Check PostgreSQL status: `pg_isready -h localhost -p 5432 -U trading_user -d trading_agent`
2. Restart PostgreSQL if needed: `brew services restart postgresql@15`
3. Verify database exists: `psql -U trading_user -d trading_agent -c "\dt"`
4. Check environment variable: `echo $DATABASE_URL`

### Issue 3: vnstock API Errors
**Symptoms**: Scanner logs show connection errors or empty data for symbols
**Steps**:
1. Test vnstock connectivity manually in Python REPL
2. Check if symbol is valid Vietnamese stock ticker
3. Verify internet connection and DNS resolution
4. Retry scan: `curl -X POST http://localhost:8200/api/scanner/scan/{SYMBOL}`

### Issue 4: FastAPI Server Not Responding
**Symptoms**: Connection refused on port 8200
**Steps**:
1. Check if process is running: `ps aux | grep uvicorn`
2. Restart server: `pkill -9 -f uvicorn && sleep 2 && uvicorn api.main:app --host 0.0.0.0 --port 8200 --reload &`
3. Verify health check: `curl http://localhost:8200/api/health`

### Issue 5: Streamlit Dashboard Not Loading
**Symptoms**: Connection refused on port 8501 or blank page
**Steps**:
1. Check if process is running: `ps aux | grep streamlit`
2. Restart dashboard: `streamlit run dashboard/app.py --server.port 8501 --server.headless true --runner.magicEnabled false &`
3. Verify accessibility: `curl http://localhost:8501/`

### Issue 6: Numpy Serialization Errors in Logs
**Symptoms**: PostgreSQL JSON column errors, "schema 'np' does not exist"
**Steps**:
1. This was fixed in _save_signal() with numpy type conversion
2. Verify fix is applied: Check services/scanner.py for type conversion code
3. Test signal save: `curl -X POST http://localhost:8200/api/scanner/scan/VNM`

## Monitoring Commands

### Quick System Health Check
```bash
# API Health
curl http://localhost:8200/api/health

# Scanner Status
curl http://localhost:8200/api/scanner/status

# Database Signal Count
psql -U trading_user -d trading_agent -c "SELECT count(*), signal_type FROM signals GROUP BY signal_type;"

# Running Services
ps aux | grep -E "(uvicorn|streamlit)" | grep -v grep
```

### Log Monitoring
```bash
# View recent system logs
curl 'http://localhost:8200/api/scanner/logs?limit=50&level=ERROR'

# Monitor scanner in real-time
watch -n 5 'curl -s http://localhost:8200/api/scanner/status | python -m json.tool'
```

### Performance Metrics
```bash
# Check signal generation rate
psql -U trading_user -d trading_agent -c "
SELECT date_trunc('hour', timestamp) as hour, count(*) 
FROM signals 
WHERE timestamp > now() - interval '24 hours' 
GROUP BY hour ORDER BY hour;"

# Check error rate
psql -U trading_user -d trading_agent -c "
SELECT count(*) as errors 
FROM system_logs 
WHERE level = 'ERROR' AND timestamp > now() - interval '24 hours';"
```

## Emergency Procedures

### Full System Restart
```bash
# Stop all services
pkill -9 -f uvicorn
pkill -9 -f streamlit

# Wait for ports to free up
sleep 3

# Start API server
uvicorn api.main:app --host 0.0.0.0 --port 8200 --reload &

# Start dashboard
streamlit run dashboard/app.py --server.port 8501 --server.headless true --runner.magicEnabled false &

# Verify all services
sleep 5
curl http://localhost:8200/api/health
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501/
```

### Database Reset (Last Resort)
```bash
# Backup current database
pg_dump -U trading_user -d trading_agent > backup_$(date +%Y%m%d).sql

# Drop and recreate
dropdb -U trading_user trading_agent
createdb -U trading_user trading_agent

# Initialize schema
python -c "from database.config import init_db; init_db()"
```

## Contact & Escalation

- **Level 1**: Follow troubleshooting steps above
- **Level 2**: Review system logs and database state
- **Level 3**: Check vnstock API status and external dependencies
- **Level 4**: Contactvnstock support for API outages
