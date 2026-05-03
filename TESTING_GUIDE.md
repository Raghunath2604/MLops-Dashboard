# ML Dashboard - Complete Testing Guide

## 🧪 Testing Overview

This document covers all testing scenarios for the ML Dashboard with PostgreSQL.

**Test Coverage:**
- ✅ API Endpoints (15 total)
- ✅ Database Operations (CRUD)
- ✅ Authentication (API keys, JWT)
- ✅ Data Archival
- ✅ Service Integration
- ✅ Performance/Load

---

## 🚀 Quick Test (2 minutes)

### 1. Start Services
```bash
./run.bat              # Windows
# or
docker-compose up -d   # Linux/Mac

# Wait 30 seconds
```

### 2. Run Quick Tests
```powershell
# PowerShell
./test-endpoints.ps1

# Or manually:
curl http://localhost:8001/health
curl http://localhost:8001/predict?text=Great
curl http://localhost:8001/status
```

### 3. Verify in Grafana
```
Open: http://localhost:3001
Login: admin/admin
Check: Prometheus & Loki data sources connected
```

---

## 📋 Full Test Suite (15 minutes)

### Phase 1: Service Startup

**Check all services running:**
```bash
docker-compose ps

# Expected output:
# STATUS: Up (all 6 services)
```

**Check logs for errors:**
```bash
docker-compose logs fastapi      # Should say "Uvicorn running"
docker-compose logs postgres     # Should say "ready to accept connections"
docker-compose logs grafana      # Should say "started"
docker-compose logs prometheus   # Should say "Starting"
docker-compose logs loki         # Should say "running"
docker-compose logs promtail     # Should say "started"
```

---

### Phase 2: Database Tests

#### Test 2.1: Database Connection
```bash
# Check PostgreSQL is responsive
docker-compose exec postgres psql -U mluser -d mldb -c "SELECT 1;"

# Expected: 1 (single result)
```

#### Test 2.2: Default User Created
```bash
# Check default user exists
docker-compose exec postgres psql -U mluser -d mldb -c "SELECT * FROM users WHERE username='default';"

# Expected: One row with username='default'
```

#### Test 2.3: Tables Created
```bash
# Check all tables exist
docker-compose exec postgres psql -U mluser -d mldb -c "\dt"

# Expected tables:
# - prediction_records
# - users
# - model_metrics
```

---

### Phase 3: API Endpoint Tests

#### Setup: Register a User
```bash
# Get API key
curl -X POST "http://localhost:8001/auth/register?username=testuser"

# Save the API_KEY from response
# Example response:
# {
#   "username": "testuser",
#   "api_key": "generated-key-here",
#   "message": "Store this API key safely..."
# }
```

#### Test 3.1: Health Check
```bash
curl http://localhost:8001/health

# Expected: 200
# {"status": "healthy", "service": "BERT Sentiment Analysis API"}
```

#### Test 3.2: Single Prediction (stores in DB)
```bash
curl "http://localhost:8001/predict?text=This%20product%20is%20amazing"

# Expected: 200
# {
#   "input_text": "This product is amazing",
#   "prediction": "POSITIVE",
#   "confidence": 0.9998,
#   "inference_time_ms": 45.23
# }

# Verify in DB:
docker-compose exec postgres psql -U mluser -d mldb -c "SELECT * FROM prediction_records ORDER BY timestamp DESC LIMIT 1;"
```

#### Test 3.3: Batch Prediction (multiple at once)
```bash
# PowerShell
$body = @("Great!", "Terrible", "It's okay") | ConvertTo-Json
Invoke-WebRequest -Uri "http://localhost:8001/batch-predict" -Method POST -Body $body -ContentType "application/json"

# Bash
curl -X POST http://localhost:8001/batch-predict \
  -H "Content-Type: application/json" \
  -d '["Great!", "Terrible", "Okay"]'

# Expected: 200 with 3 predictions
# Verify in DB:
docker-compose exec postgres psql -U mluser -d mldb -c "SELECT COUNT(*) FROM prediction_records;"
```

#### Test 3.4: Query Predictions
```bash
# List all predictions
curl "http://localhost:8001/predictions?limit=10"

# Expected: 200
# {
#   "predictions": [...],
#   "count": N,
#   "offset": 0,
#   "limit": 10
# }

# Query with filters
curl "http://localhost:8001/predictions?confidence_min=0.95&prediction_type=POSITIVE&limit=5"

# Should return only high-confidence POSITIVE predictions
```

#### Test 3.5: Export Data
```bash
# Export as JSON
curl -X POST "http://localhost:8001/predictions/export?format=json" > predictions.json

# Export as CSV
curl -X POST "http://localhost:8001/predictions/export?format=csv" > predictions.csv

# Verify file created
ls -la predictions.json
cat predictions.csv
```

#### Test 3.6: Historical Statistics
```bash
curl "http://localhost:8001/predictions/stats"

# Expected: 200
# {
#   "statistics": [
#     {
#       "date": "2026-04-23",
#       "predictions_count": 5,
#       "avg_confidence": 0.9745,
#       "avg_inference_time_ms": 44.2
#     }
#   ],
#   "total_records": 1
# }
```

#### Test 3.7: Authentication Flow
```bash
# Login with credentials (API key from register)
curl -X POST "http://localhost:8001/auth/login?username=testuser&api_key=YOUR_API_KEY"

# Expected: 200
# {
#   "access_token": "jwt-token-here",
#   "token_type": "bearer",
#   "username": "testuser"
# }
```

#### Test 3.8: Service Status
```bash
curl "http://localhost:8001/status"

# Expected: 200
# {
#   "services": {
#     "postgres": {"status": "operational"},
#     "prometheus": {"status": "operational"},
#     "loki": {"status": "operational"},
#     "api": {"status": "operational"}
#   },
#   "overall_status": "healthy"
# }
```

#### Test 3.9: Prometheus Metrics
```bash
curl "http://localhost:8001/metrics" | head -20

# Expected: 200 with Prometheus format
# # HELP request_count_total Total API Requests
# request_count_total 15.0
# # HELP error_count_total Total API Errors
# error_count_total 0.0
```

#### Test 3.10: Drilldown Metrics
```bash
curl "http://localhost:8001/drilldown"

# Expected: 200
# {
#   "request_count": 15.0,
#   "error_count": 0.0,
#   "latency_stats": {
#     "total": 5.2,
#     "count": 15,
#     "average": 0.347
#   },
#   "status": "operational"
# }
```

---

### Phase 4: Integration Tests

#### Test 4.1: End-to-End Prediction Flow
```bash
# 1. Make predictions
for i in {1..5}; do
  curl "http://localhost:8001/predict?text=Test%20text%20$i"
done

# 2. Query predictions
curl "http://localhost:8001/predictions"

# 3. Check metrics
curl "http://localhost:8001/metrics" | grep request_count_total

# 4. Check status
curl "http://localhost:8001/status"

# All should succeed
```

#### Test 4.2: Metrics Flow (Prometheus)
```bash
# 1. Make requests to API
curl http://localhost:8001/predict?text=test

# 2. Access metrics endpoint
curl http://localhost:8001/metrics

# 3. Check Prometheus
curl http://localhost:9091/api/v1/query?query=request_count_total

# Expected: should show increased counter
```

#### Test 4.3: Logging Flow (Loki)
```bash
# 1. Make prediction
curl "http://localhost:8001/predict?text=test"

# 2. Check app logs
docker-compose logs -f fastapi

# Should see: "Prediction Success | Input=test | Output=..."

# 3. Check Loki has logs
curl "http://localhost:3011/loki/api/v1/query?query={job=\"model_logs\"}"

# Expected: logs should appear in Loki
```

#### Test 4.4: Database Archival (Test archival job)
```bash
# 1. Make predictions
for i in {1..10}; do
  curl "http://localhost:8001/predict?text=Test%20$i"
done

# 2. Run archive job manually
docker-compose exec fastapi python archive_job.py

# 3. Check ModelMetrics table was updated
docker-compose exec postgres psql -U mluser -d mldb \
  -c "SELECT * FROM model_metrics ORDER BY date DESC;"

# Expected: daily aggregate record created
```

---

### Phase 5: Load Testing

#### Test 5.1: Basic Load Test (100 requests)
```bash
# Using hey tool
hey -n 100 -c 10 "http://localhost:8001/predict?text=test"

# Expected output shows:
# - Status 200: 100
# - Latency: ~40-50ms average
# - Errors: 0
```

#### Test 5.2: Concurrent Users (50 parallel)
```bash
# 50 concurrent requests
hey -n 500 -c 50 "http://localhost:8001/predict?text=concurrent%20test"

# Expected:
# - Response time < 500ms
# - No errors
# - CPU/Memory stable
```

#### Test 5.3: Batch Prediction Load
```bash
# Generate large batch
seq 1 100 | awk '{print "\"Text "$1"\""}' > batch.json

# Send batch
curl -X POST http://localhost:8001/batch-predict \
  -H "Content-Type: application/json" \
  -d @batch.json

# Expected: all 100 processed successfully
```

---

### Phase 6: Error Handling Tests

#### Test 6.1: Invalid Input
```bash
# Empty text
curl "http://localhost:8001/predict?text="

# Expected: Should handle gracefully or return 400
```

#### Test 6.2: Database Disconnect
```bash
# Simulate by stopping postgres
docker-compose stop postgres

# Try to make prediction
curl "http://localhost:8001/predict?text=test"

# Expected: 500 error with descriptive message
# Check status shows postgres: unreachable

# Restart postgres
docker-compose start postgres

# Predictions should work again after reconnection
```

#### Test 6.3: Invalid Credentials
```bash
# Wrong API key
curl -X POST "http://localhost:8001/auth/login?username=testuser&api_key=wrong-key"

# Expected: 401 Unauthorized
```

---

### Phase 7: Grafana Integration Tests

#### Test 7.1: Verify Data Sources
```
1. Open http://localhost:3001
2. Login: admin/admin
3. Go to Configuration → Data Sources
4. Expected to see:
   - Prometheus (http://prometheus:9090) - ✓ Green
   - Loki (http://loki:3100) - ✓ Green
```

#### Test 7.2: Query Prometheus
```
1. In Grafana, open Explore
2. Select Prometheus data source
3. Run query: request_count_total
4. Expected: Graph shows increasing counter
```

#### Test 7.3: Query Loki
```
1. In Grafana, open Explore
2. Select Loki data source
3. Run query: {job="model_logs"}
4. Expected: Recent logs from FastAPI appear
```

---

## ✅ Automated Test Script

Create `run_tests.sh`:

```bash
#!/bin/bash

echo "=== ML Dashboard Test Suite ==="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

TESTS_PASSED=0
TESTS_FAILED=0

test_endpoint() {
    local name=$1
    local url=$2
    local expected_code=$3

    echo -n "Testing $name... "
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    
    if [ "$response" == "$expected_code" ]; then
        echo -e "${GREEN}PASS${NC} ($response)"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}FAIL${NC} (got $response, expected $expected_code)"
        ((TESTS_FAILED++))
    fi
}

# Run tests
test_endpoint "Health" "http://localhost:8001/health" "200"
test_endpoint "Predict" "http://localhost:8001/predict?text=test" "200"
test_endpoint "Status" "http://localhost:8001/status" "200"
test_endpoint "Predictions" "http://localhost:8001/predictions" "200"
test_endpoint "Metrics" "http://localhost:8001/metrics" "200"

echo ""
echo "=== Test Results ==="
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"

exit $TESTS_FAILED
```

Run tests:
```bash
chmod +x run_tests.sh
./run_tests.sh
```

---

## 📊 Performance Benchmarks (Expected)

| Endpoint | Latency | Throughput | Notes |
|----------|---------|-----------|-------|
| `/health` | <5ms | >1000 req/s | lightweight |
| `/predict` | 40-50ms | 50-100 req/s | ML model inference |
| `/batch-predict` | 40-50ms × N | scales linearly | efficient batch |
| `/predictions` | 10-20ms | >500 req/s | database query |
| `/status` | 5-10ms | >1000 req/s | lightweight |
| `/metrics` | 5-10ms | >1000 req/s | in-memory |

---

## 🔍 Debugging Tips

### Check Service Logs
```bash
docker-compose logs fastapi -f      # Follow FastAPI logs
docker-compose logs postgres -f     # Follow PostgreSQL logs
docker-compose logs grafana -f      # Follow Grafana logs
```

### Access PostgreSQL Directly
```bash
docker-compose exec postgres psql -U mluser -d mldb

# Useful queries:
SELECT COUNT(*) FROM prediction_records;
SELECT * FROM users;
SELECT * FROM model_metrics ORDER BY date DESC LIMIT 5;
SELECT * FROM prediction_records WHERE timestamp > NOW() - INTERVAL '1 hour';
```

### Check Docker Network
```bash
# Verify services can communicate
docker network ls
docker network inspect mldashborad_monitoring

# Test DNS
docker-compose exec fastapi ping postgres
docker-compose exec fastapi curl http://prometheus:9090/-/healthy
```

### Monitor Resource Usage
```bash
docker stats

# Shows CPU, Memory, Network for each container
```

---

## ✨ Test Checklist for Release

Before releasing to production:

- [ ] All 15 API endpoints return 200 (success cases)
- [ ] All services start without errors
- [ ] Database initializes with default user
- [ ] Predictions stored in PostgreSQL
- [ ] Prometheus collects metrics
- [ ] Loki stores logs
- [ ] Grafana dashboards display data
- [ ] Load test: 100 concurrent requests
- [ ] Error handling: graceful 500s on database failure
- [ ] Authentication: API keys and JWT tokens work
- [ ] Export: CSV and JSON formats correct
- [ ] Archival: daily aggregates calculated
- [ ] Backup: PostgreSQL backup tested
- [ ] Monitoring: Grafana alerts configured
- [ ] Documentation: all endpoints documented

