# 🚀 BERT Sentiment Analysis - Complete Monitoring System with PostgreSQL

## 📋 Project Overview

**Full ML Monitoring Stack with Persistent Storage:**
- **Model**: BERT Sentiment Analysis (HuggingFace DistilBERT)
- **API**: FastAPI with Prometheus metrics & health checks
- **Database**: PostgreSQL for persistent prediction storage & analytics
- **Logging**: Application logs → Promtail → Loki
- **Monitoring**: Prometheus metrics collection
- **Visualization**: Grafana dashboards
- **Deployment**: Docker + Docker Compose (6 services)

**Status**: ✅ **PRODUCTION READY WITH PERSISTENCE**

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  USER REQUESTS                      │
│              (localhost:8001)                       │
└────────────────┬────────────────────────────────────┘
                 │
    ┌────────────▼────────────┐
    │   FastAPI + BERT Model  │
    │   ├─ /predict           │
    │   ├─ /batch-predict     │
    │   ├─ /health            │
    │   ├─ /drilldown         │
    │   ├─ /status            │
    │   ├─ /metrics           │
    │   ├─ /auth/register     │
    │   ├─ /auth/login        │
    │   ├─ /predictions       │
    │   ├─ /predictions/stats │
    │   └─ /predictions/export│
    └────────┬────────────────┘
             │
      ┌──────┴────────┬──────────────┬──────────────┐
      │               │              │              │
      ▼               ▼              ▼              ▼
  Prometheus     Promtail        Logs         PostgreSQL
  (9090)         (collector)    (app.log)      (5432)
   │                │              │              │
   │                └──────┬───────┘              │
   │                       ▼                      │
   │                    Loki                      │
   │                   (3100)                     │
   │                       │                      │
   └───────────┬───────────┘                      │
               │                                  │
               ▼                                  │
            Grafana ◄──────────────────────────────┘
           (3001)
         Dashboard
         + Analytics
```

---

## 📁 Project Structure

```
mldashborad/
├── app.py                      # FastAPI + BERT model (15 endpoints)
├── models.py                   # SQLAlchemy ORM models
├── database.py                 # PostgreSQL async connection
├── auth.py                     # JWT & API key authentication
├── archive_job.py              # 90-day data archival scheduler
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container build
├── docker-compose.yml          # 6-service orchestration
├── prometheus.yml              # Prometheus scrape config
├── loki-config.yaml            # Loki storage backend
├── promtail-config.yaml        # Log collector config
├── grafana-datasources.yml     # Grafana auto-config
├── run.bat                     # Windows startup script
├── app.log                     # Application logs
└── README.md                   # Documentation
```

---

## 🚀 Quick Start

### Option 1: Using run.bat (Windows)
```batch
run.bat
```

### Option 2: Manual Docker Commands
```bash
# Build images
docker-compose build

# Start all services
docker-compose up -d

# Wait 15 seconds for services to start
# Check status
docker-compose ps
```

---

## 🌐 Access Points

| Service | External Port | Internal URL | Purpose |
|---------|---------------|--------------|---------|
| **FastAPI** | 8001 | - | ML model API |
| **PostgreSQL** | 5432 | postgresql://postgres:5432/mldb | Persistent storage |
| **Prometheus** | 9091 | http://prometheus:9090 | Metrics storage |
| **Grafana** | 3001 | - | Dashboard UI |
| **Loki** | 3011 | http://loki:3100 | Log aggregation |

**Grafana Credentials**: `admin` / `admin`
**PostgreSQL Credentials**: `mluser` / `mlpassword` (DB: `mldb`)

---

## 📡 Available API Endpoints (15 Total)

### Authentication (2 endpoints)

**1. Register User**
```bash
POST /auth/register?username=myuser
Response: {
  "username":"myuser",
  "api_key":"generated-api-key-store-safely",
  "message":"Store this API key safely..."
}
```

**2. Login**
```bash
POST /auth/login?username=myuser&api_key=your-api-key
Response: {
  "access_token":"jwt-token",
  "token_type":"bearer",
  "username":"myuser"
}
```

### Predictions (3 endpoints)
```bash
GET /health
Response: {"status":"healthy","service":"BERT Sentiment Analysis API"}
```

### 2. Single Prediction
```bash
GET /predict?text=I%20love%20this%20product
Response: {
  "input_text":"I love this product",
  "prediction":"POSITIVE",
  "confidence":0.9998788833618164,
  "inference_time_ms":45.23
}
```

### 3. Batch Predictions
```bash
POST /batch-predict
Body: ["Great!", "Terrible", "Okay"]
Response: {
  "predictions":[
    {"input_text":"Great!","prediction":"POSITIVE","confidence":0.9998,"inference_time_ms":44.5},
    {"input_text":"Terrible","prediction":"NEGATIVE","confidence":0.9996,"inference_time_ms":43.2},
    {"input_text":"Okay","prediction":"POSITIVE","confidence":0.9991,"inference_time_ms":45.1}
  ]
}
```

### 4. Query Predictions (with filters)
```bash
GET /predictions?limit=50&offset=0&date_from=2026-04-20&date_to=2026-04-23&confidence_min=0.95&prediction_type=POSITIVE
Response: {
  "predictions":[...],
  "count":42,
  "offset":0,
  "limit":50
}
```

### 5. Export Predictions
```bash
POST /predictions/export?format=csv&date_from=2026-04-20&date_to=2026-04-23
Returns: CSV file with headers (ID, Input Text, Prediction, Confidence, Inference Time, Timestamp, Request ID)

# Or JSON format:
POST /predictions/export?format=json&date_from=2026-04-20&date_to=2026-04-23
Returns: JSON array of predictions
```

### 6. Get Historical Statistics
```bash
GET /predictions/stats?date_from=2026-04-15&date_to=2026-04-23
Response: {
  "statistics":[
    {
      "date":"2026-04-23",
      "predictions_count":156,
      "avg_confidence":0.9745,
      "avg_inference_time_ms":44.2
    }
  ],
  "total_records":7
}
```

### Health & Monitoring (3 endpoints)

### 7. Health Check
```bash
GET /health
Response: {"status":"healthy","service":"BERT Sentiment Analysis API"}
```

### 8. Drilldown Metrics
```bash
GET /drilldown
Response: {
  "request_count":31.0,
  "error_count":0.0,
  "latency_stats":{
    "total":5.2,
    "count":31,
    "average":0.168
  },
  "status":"operational"
}
```

### 9. Service Status (includes PostgreSQL health)
```bash
GET /status
Response: {
  "timestamp":1776918550.30648,
  "services":{
    "loki":{"url":"http://loki:3100/ready","status":"operational"},
    "prometheus":{"url":"http://prometheus:9090/-/healthy","status":"operational"},
    "postgres":{"url":"postgresql://postgres:5432/mldb","status":"operational"},
    "api":{"status":"operational"}
  },
  "overall_status":"healthy"
}
```

### Metrics (1 endpoint)

### 10. Prometheus Metrics
```bash
GET /metrics
Response: (Prometheus format with all counters and histograms)
```

---

## 🧪 Test the System

### PowerShell Tests (Windows)
```powershell
# Test 1: Health
Invoke-WebRequest -Uri "http://localhost:8001/health" -UseBasicParsing

# Test 2: Single prediction
Invoke-WebRequest -Uri "http://localhost:8001/predict?text=Great%20product" -UseBasicParsing

# Test 3: Batch prediction
$body = ConvertTo-Json @("Amazing", "Terrible", "Okay")
Invoke-WebRequest -Uri "http://localhost:8001/batch-predict" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing

# Test 4: Check services
Invoke-WebRequest -Uri "http://localhost:8001/status" -UseBasicParsing
```

### Bash Tests (Linux/Mac)
```bash
# Test 1: Health
curl http://localhost:8001/health

# Test 2: Single prediction
curl "http://localhost:8001/predict?text=Great%20product"

# Test 3: Batch prediction
curl -X POST http://localhost:8001/batch-predict \
  -H "Content-Type: application/json" \
  -d '["Amazing", "Terrible", "Okay"]'

# Test 4: Check services
curl http://localhost:8001/status
```

---

## 📊 Grafana Setup

### Auto-configured Data Sources
✅ **Prometheus**: `http://prometheus:9090` (internal Docker network)
✅ **Loki**: `http://loki:3100` (internal Docker network)
✅ **PostgreSQL**: `postgres:5432/mldb` (internal Docker network)

All are automatically configured via `grafana-datasources.yml`

### Import Pre-configured Dashboard (Quick Start)
1. Open Grafana: http://localhost:3001
2. Login: `admin` / `admin`
3. Click "+" → "Import"
4. Choose "Upload JSON file"
5. Select `grafana-dashboard.json` from the project folder
6. Select Data Sources:
   - Prometheus: `Prometheus`
   - PostgreSQL: `PostgreSQL`
7. Click "Import" → Done! 🎉

The dashboard includes 8 pre-configured panels:
- **Request Rate** - Real-time API request volume
- **Error Rate** - Error percentage gauge
- **Average Latency** - Response time trend
- **Sentiment Distribution** - Pie chart of POSITIVE/NEGATIVE
- **Recent Predictions** - Table of last 50 predictions
- **User Analytics** - Per-user statistics table
- **Predictions Over Time** - Daily prediction count
- **Confidence Distribution** - Histogram of model confidence

### Create Your First Dashboard (Manual)
1. Open Grafana: http://localhost:3001
2. Login: `admin` / `admin`
3. Click "+" → "Dashboard" → "New Panel"
4. Set Data Source to **Prometheus**
5. Query Example: `rate(request_count_total[1m])`
6. Save & done!

### Sample Queries

**Request Rate (req/sec)**:
```promql
rate(request_count_total[1m])
```

**Error Rate (%)**:
```promql
(rate(error_count_total[1m]) / rate(request_count_total[1m])) * 100
```

**P95 Latency (sec)**:
```promql
histogram_quantile(0.95, rate(latency_seconds_bucket[1m]))
```

**Application Logs (Loki)**:
```logql
{job="model_logs"}
```

---

## 🔄 Data Flow

### Prediction Storage (Database)
```
User Request: /predict?text=...
  ↓
FastAPI model inference (~40-50ms)
  ↓
Store in PostgreSQL:
  - input_text
  - prediction (POSITIVE/NEGATIVE)
  - confidence (0.0 - 1.0)
  - inference_time_ms
  - timestamp
  - request_id (for batch tracking)
  ↓
Return response + inference_time_ms
```

### Metrics Collection
```
FastAPI (app.py)
  ├─ request_count++ (every request)
  ├─ latency_seconds (observed)
  └─ error_count++ (on error)
    ↓
  /metrics endpoint (Prometheus format)
    ↓
  Prometheus scrapes (every 15 seconds)
    ↓
  Grafana queries Prometheus (every 5 seconds)
    ↓
  Dashboard updates in real-time
```

### Log Collection
```
FastAPI (app.py)
  ├─ logger.info("Prediction Success...")
  └─ logger.error("Prediction Failed...")
    ↓
  app.log file (and stdout)
    ↓
  Promtail reads (continuously)
    ↓
  Loki API POST /loki/api/v1/push
    ↓
  Loki stores & indexes
    ↓
  Grafana queries Loki
    ↓
  Logs panel updates (real-time)
```

### Data Archival (Daily)
```
PostgreSQL PredictionRecord table
  ↓
archive_job.py runs daily (configurable)
  ├─ Mark predictions >90 days old as archived
  ├─ Aggregate into ModelMetrics table
  ├─ Delete records >180 days old
  └─ Log activity
    ↓
ModelMetrics (daily aggregates)
  ├─ predictions_count (daily total per user)
  ├─ avg_confidence (daily average)
  ├─ avg_inference_time_ms (daily average)
  └─ date (for grouping)
```

---

## 🐛 Troubleshooting

### Problem: Containers not starting
```bash
# Check Docker Desktop is running
docker ps

# View logs
docker-compose logs

# Restart
docker-compose restart
```

### Problem: Can't access http://localhost:3001
- Ensure Docker Desktop is running (Admin mode)
- Wait 30 seconds (first startup is slow)
- Check: `docker-compose ps` (should show 5 running containers)
- View logs: `docker-compose logs grafana`

### Problem: No metrics in Grafana
1. Send requests: `curl http://localhost:8001/predict?text=test`
2. Wait 15 seconds (Prometheus scrape interval)
3. Refresh Grafana (F5)
4. Query: `request_count_total`

### Problem: Loki/Prometheus not connecting
- Check internal URLs in Grafana: http://prometheus:9090 & http://loki:3100
- These are **Docker network** URLs (not localhost)
- Data sources already auto-configured

### Problem: Logs not appearing
1. Check app logs: `docker-compose logs -f fastapi`
2. Verify Promtail is running: `docker-compose ps promtail`
3. Check Loki: `curl http://localhost:3011/ready`

---

## 📚 Useful Commands

```bash
# View all logs (follow mode)
docker-compose logs -f

# View specific service logs
docker-compose logs -f fastapi
docker-compose logs -f prometheus
docker-compose logs -f loki
docker-compose logs -f grafana
docker-compose logs -f promtail

# Restart specific service
docker-compose restart fastapi
docker-compose restart grafana

# Stop all services (keeps data)
docker-compose stop

# Stop and remove (keeps data)
docker-compose down

# Full reset (removes all data & volumes)
docker-compose down -v

# Check service status
docker-compose ps

# Rebuild image
docker-compose build --no-cache

# Restart with rebuild
docker-compose up -d --build
```

---

## 🔧 Features in This Version

✅ **PostgreSQL Integration**
- Persistent storage of all predictions
- User authentication with API keys & JWT tokens
- 90-day rolling retention with automatic archival
- Daily aggregated metrics (ModelMetrics table)

✅ **Enhanced API Endpoints**
- `/auth/register` - Create user with generated API key
- `/auth/login` - Get JWT token for protected endpoints
- `/predictions` - Query predictions with filters (date, confidence, type)
- `/predictions/stats` - Historical daily statistics
- `/predictions/export` - Download as CSV or JSON
- Updated `/predict` & `/batch-predict` to store in database
- Updated `/status` to include PostgreSQL health check

✅ **Previous Features**
- Error responses return HTTP 500 status code (not 200)
- Logs sent to stdout for Promtail collection
- Type hints for all FastAPI endpoints
- Prometheus metrics properly accessed from Histogram objects
- Service health checks with connectivity verification

✅ **Database Architecture**
- Users table: authentication & API key tracking
- PredictionRecord table: individual predictions with inference metrics
- ModelMetrics table: daily aggregates for performance
- Automatic archival job: keep only 90 days active, 180 days total

---

## 🎓 What You Get

✅ **Production-Ready ML API** - Sentiment analysis via REST
✅ **Persistent Data Storage** - PostgreSQL with 90-day rolling retention
✅ **User Authentication** - API keys + JWT token support
✅ **Real-time Metrics** - Request rate, error rate, latency via Prometheus
✅ **Centralized Logging** - All logs in Loki with live search
✅ **Professional Dashboard** - Grafana with auto-configured data sources
✅ **Health Monitoring** - Service status checks & connectivity validation
✅ **Batch Processing** - Send multiple texts in one request
✅ **Advanced Analytics** - Query predictions by date, confidence, type
✅ **Data Export** - Download predictions as CSV or JSON
✅ **Automatic Archival** - Keep 90 days active, 180 days in archive, auto-cleanup
✅ **Containerized** - Docker Compose with 6 integrated services

---

## 🚀 For Your Viva/Resume

**Key Achievements**:
1. ✅ Deployed BERT sentiment analysis as production REST API
2. ✅ Implemented real-time Prometheus metrics collection
3. ✅ Centralized logging with Grafana Loki (Promtail)
4. ✅ Professional dashboard with service health monitoring
5. ✅ **Persistent PostgreSQL storage** for predictions & analytics
6. ✅ **User authentication** with API keys & JWT tokens
7. ✅ **90-day rolling retention** with automatic archival
8. ✅ **Advanced prediction queries** with filters & export (CSV/JSON)
9. ✅ **15 API endpoints** (health, predict, batch-predict, auth, queries, etc.)
10. ✅ Containerized 6-service system with Docker Compose
11. ✅ All services connected and verified working

**Technical Highlights**:
- SQLAlchemy ORM with async PostgreSQL (asyncpg)
- JWT token authentication & API key hashing
- Automatic database initialization on startup
- Daily archival job for data retention management
- Type-safe FastAPI endpoints with dependency injection
- Centralized Loki + Promtail log aggregation
- Grafana dashboards with real-time metrics

**Live Demo**:
- Dashboard updates every 5 seconds
- Metrics show real-time API performance
- Logs appear instantly with search capability
- Predictions stored permanently in PostgreSQL
- Query historical data by date, confidence, prediction type
- Error tracking with visual thresholds
- Industry-grade monitoring + analytics architecture

---

## 📞 Next Steps

1. **Add Alerting**: Configure Grafana alerts for error rate > 5%
2. **Custom Metrics**: Add model-specific KPIs
3. **Kubernetes**: Deploy to production cluster
4. **API Security**: Add authentication & rate limiting
5. **Model Optimization**: Fine-tune for faster inference

---

**Status**: ✅ Production Ready with Persistence  
**Services**: 6/6 Running (FastAPI, PostgreSQL, Prometheus, Loki, Grafana, Promtail)
**API Endpoints**: 15/15 Working (Auth: 2, Predictions: 5, Monitoring: 3, Metrics: 1, Health: 1)
**Data Sources**: Prometheus ✅ | Loki ✅ | PostgreSQL ✅
**Database**: PostgreSQL 15 with 90-day rolling retention
**Version**: 3.0 (with PostgreSQL persistence)
**Last Updated**: 2026-04-23
