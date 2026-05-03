# ML Dashboard - Quick Reference Card

## 📦 Project Status
- ✅ **Version**: 3.0 (PostgreSQL + Auth)
- ✅ **Services**: 6 (FastAPI, PostgreSQL, Prometheus, Loki, Grafana, Promtail)
- ✅ **API Endpoints**: 15
- ✅ **Database**: PostgreSQL 15 with 90-day retention
- ✅ **Production Ready**: Yes

---

## 🚀 Start Services
```bash
./run.bat              # Windows
docker-compose up -d   # Linux/Mac
```

---

## 🌐 Access Points
| Service | URL | Login |
|---------|-----|-------|
| **API** | http://localhost:8001 | - |
| **Grafana** | http://localhost:3001 | admin/admin |
| **Prometheus** | http://localhost:9091 | - |
| **Loki** | http://localhost:3011 | - |
| **PostgreSQL** | localhost:5432 | mluser/mlpassword |

---

## 📡 API Endpoints (15)

### Authentication (2)
```bash
# Register (get API key)
POST /auth/register?username=name

# Login (get JWT token)
POST /auth/login?username=name&api_key=key
```

### Predictions (5)
```bash
# Single prediction (stores in DB)
GET /predict?text=...

# Batch prediction
POST /batch-predict  [array of texts]

# Query predictions (with filters)
GET /predictions?limit=10&confidence_min=0.95&prediction_type=POSITIVE&date_from=2026-04-20

# Get daily statistics
GET /predictions/stats

# Export as CSV or JSON
POST /predictions/export?format=csv|json
```

### Monitoring (3)
```bash
# Health check
GET /health

# Service status (includes DB)
GET /status

# Drilldown metrics
GET /drilldown
```

### Metrics (1)
```bash
# Prometheus format
GET /metrics
```

### Home (1)
```bash
# Info endpoint
GET /
```

---

## 🗄️ Database Schema

**users**
- id (PK)
- username (unique)
- api_key (hashed, unique)
- created_at

**prediction_records**
- id (PK)
- user_id (FK)
- input_text
- prediction (POSITIVE/NEGATIVE)
- confidence (0.0-1.0)
- inference_time_ms
- timestamp (indexed)
- request_id (UUID)
- archived (boolean)

**model_metrics** (daily aggregates)
- id (PK)
- user_id (FK)
- predictions_count
- avg_confidence
- avg_inference_time_ms
- date (indexed)

---

## 🧪 Quick Test

```bash
# Check all services
docker-compose ps

# Test API
curl http://localhost:8001/health
curl "http://localhost:8001/predict?text=Great"
curl http://localhost:8001/status

# Run full test suite
./test-endpoints.ps1   # PowerShell

# Check database
docker-compose exec postgres psql -U mluser -d mldb -c "SELECT COUNT(*) FROM prediction_records;"

# Follow logs
docker-compose logs -f fastapi
```

---

## 📊 Grafana Queries

```promql
# Request rate (per second)
rate(request_count_total[1m])

# Error rate (%)
(rate(error_count_total[1m]) / rate(request_count_total[1m])) * 100

# P95 latency
histogram_quantile(0.95, rate(latency_seconds_bucket[1m]))

# Loki logs
{job="model_logs"} | json
```

---

## 🔒 Environment Variables (.env)

```
DATABASE_URL=postgresql+asyncpg://mluser:mlpassword@postgres:5432/mldb
SECRET_KEY=your-secure-key-here
PROMETHEUS_URL=http://prometheus:9090
LOKI_URL=http://loki:3100
LOG_LEVEL=INFO
```

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `app.py` | FastAPI application (15 endpoints) |
| `models.py` | SQLAlchemy ORM models |
| `database.py` | PostgreSQL connection + session |
| `auth.py` | JWT + API key authentication |
| `archive_job.py` | Daily archival scheduler |
| `docker-compose.yml` | 6-service orchestration |
| `.env` | Environment variables (secrets) |

---

## 🔄 Data Flow

```
User Request
  ↓
FastAPI Inference (40-50ms)
  ↓
Store in PostgreSQL
  ↓
Update Prometheus metrics
  ↓
Log to stdout/Promtail
  ↓
Loki aggregates logs
  ↓
Grafana visualizes
```

---

## 📋 Maintenance Commands

```bash
# View logs
docker-compose logs -f fastapi

# Restart service
docker-compose restart fastapi

# Stop all services
docker-compose stop

# Full reset (removes data!)
docker-compose down -v

# Build images
docker-compose build --no-cache

# Database backup
docker-compose exec postgres pg_dump -U mluser mldb > backup.sql

# List predictions in DB
docker-compose exec postgres psql -U mluser -d mldb \
  -c "SELECT * FROM prediction_records ORDER BY timestamp DESC LIMIT 10;"

# Run archive job manually
docker-compose exec fastapi python archive_job.py
```

---

## ⚙️ Configuration

### Change SECRET_KEY (for security)
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Copy output to .env
```

### Change PostgreSQL credentials
```yaml
# docker-compose.yml
environment:
  POSTGRES_USER: newuser
  POSTGRES_PASSWORD: newpassword
  POSTGRES_DB: mydb
```

### Change ports
```yaml
# docker-compose.yml
services:
  fastapi:
    ports:
      - "8080:8000"  # Change from 8001 to 8080
```

---

## 🚨 Troubleshooting

| Problem | Solution |
|---------|----------|
| Services won't start | `docker-compose logs` to check errors |
| PostgreSQL connection error | Wait 30 seconds, DB might be initializing |
| Can't access Grafana | Make sure port 3001 is available |
| Predictions not stored | Check PostgreSQL is running: `docker-compose ps postgres` |
| Logs not in Loki | Check Promtail: `docker-compose logs promtail` |
| Metrics not in Prometheus | Send requests first: `curl http://localhost:8001/predict?text=test` |
| High latency | Check system resources: `docker stats` |

---

## 📈 Performance Targets

| Endpoint | Latency | Notes |
|----------|---------|-------|
| `/health` | <5ms | Fast |
| `/predict` | 40-50ms | Model inference |
| `/predictions` | 10-20ms | Database query |
| `/status` | 5-10ms | Fast |
| `/metrics` | 5-10ms | In-memory |

**Throughput**: 50-100 predictions/sec on typical hardware

---

## 📞 Important Notes

- ⚠️ `.env` contains secrets - **never commit to git**
- ⚠️ Default user `mluser/mlpassword` - **change in production**
- ⚠️ Predictions automatically archived after 90 days
- ⚠️ Archived records deleted after 180 days
- ℹ️ Database initialized automatically on startup
- ℹ️ Metrics collected every 15 seconds
- ℹ️ Logs shipped to Loki continuously

---

## 📚 Documentation Files

- `README.md` - Full project overview
- `DEPLOYMENT_GUIDE.md` - Production deployment
- `TESTING_GUIDE.md` - Comprehensive testing
- `DATABASE_SCHEMA.sql` - SQL schema reference
- `.env.example` - Environment template

---

**Last Updated**: 2026-04-23  
**Status**: ✅ Production Ready
