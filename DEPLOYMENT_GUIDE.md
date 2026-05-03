# ML Dashboard - Deployment & Production Guide

## 🚀 Quick Start (Development)

### Local Development with Docker Compose
```bash
# 1. Clone/navigate to project
cd mldashborad

# 2. Start all services
./run.bat              # Windows
# or
docker-compose up -d   # Linux/Mac

# 3. Wait 30 seconds for services to be ready
# 4. Check status
docker-compose ps

# 5. Test endpoints
curl http://localhost:8001/health
```

---

## 📋 Pre-Deployment Checklist

- [ ] `.env` file created with secure `SECRET_KEY`
- [ ] PostgreSQL credentials set in `.env` and `docker-compose.yml`
- [ ] All 6 services can start without errors
- [ ] Database initializes and creates default user
- [ ] All 15 API endpoints respond
- [ ] Grafana dashboards load
- [ ] Predictions are stored in PostgreSQL
- [ ] Archive job configured

---

## 🔧 Production Deployment

### Option A: Docker Compose (Recommended for small-medium deployments)

**Step 1: Prepare environment**
```bash
# Copy and customize .env
cp .env.example .env
# Edit .env with production values:
# - Change SECRET_KEY to a new secure value
# - Update DATABASE_URL if using external PostgreSQL
# - Update credentials

# Generate new SECRET_KEY for production
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Step 2: Update docker-compose for production**
```yaml
# docker-compose.yml changes:

services:
  fastapi:
    environment:
      - ENVIRONMENT=production
    # Add health check
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    # Backup strategy
    environment:
      POSTGRES_INITDB_ARGS: "-c shared_preload_libraries=pg_stat_statements"
    volumes:
      - postgres_backups:/backups  # Add backup volume
```

**Step 3: Deploy**
```bash
# Pull latest images
docker-compose pull

# Start services
docker-compose up -d

# Verify
docker-compose ps
docker-compose logs -f fastapi

# Run migrations (if any)
# docker-compose exec fastapi python archive_job.py
```

**Step 4: Set up monitoring alerts**
```bash
# In Grafana:
1. Go to Alerting → Alert Rules
2. Create alerts for:
   - PostgreSQL connection failures
   - High error rate (>5%)
   - High latency (>500ms)
   - Prediction archival failures
```

---

### Option B: Kubernetes Deployment (for enterprise)

**Create Kubernetes manifests:**

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-dashboard
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ml-dashboard
  template:
    metadata:
      labels:
        app: ml-dashboard
    spec:
      containers:
      - name: fastapi
        image: ml-dashboard:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: connection-string
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: app-secret
              key: secret-key
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
# k8s/postgres-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: ml-dashboard-postgres
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          value: mldb
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: username
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: password
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
```

**Deploy to K8s:**
```bash
# Create secrets
kubectl create secret generic db-secret \
  --from-literal=connection-string='postgresql://...' \
  --from-literal=username=mluser \
  --from-literal=password=mlpassword

kubectl create secret generic app-secret \
  --from-literal=secret-key='your-secure-key'

# Deploy
kubectl apply -f k8s/

# Verify
kubectl get pods
kubectl logs deployment/ml-dashboard
```

---

## 🔒 Security Hardening (Production)

### 1. PostgreSQL Security
```sql
-- Restrict connections
ALTER USER mluser CONNECTION LIMIT 10;

-- Create read-only user for analytics
CREATE USER analytics_user WITH PASSWORD 'analytics_password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_user;

-- Enable SSL
-- Update postgresql.conf: ssl = on
-- Copy certificate files to postgres container
```

### 2. FastAPI Security
```python
# Add to app.py for production:
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/login")
@limiter.limit("5/minute")  # Rate limit login attempts
async def login(...):
    ...

# Enable HTTPS/TLS
# Use nginx reverse proxy with SSL certificates
```

### 3. Environment Variables
```bash
# Never commit .env
git config core.hooksPath .githooks

# Rotate secrets regularly
# Store in HashiCorp Vault or AWS Secrets Manager
```

### 4. Network Security
```yaml
# docker-compose.yml
networks:
  monitoring:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.enable_ip_masquerade: "true"

# Expose only necessary ports
# 8001 (FastAPI) → public
# 5432 (PostgreSQL) → internal only
# 3001 (Grafana) → public (with auth)
# 9090 (Prometheus) → internal only
```

---

## 📊 Monitoring & Alerts (Production)

### Grafana Alerts
```
Alert: High Error Rate
Condition: error_count_total > 5% of request_count_total
Duration: 5 minutes
Action: Send to Slack webhook

Alert: PostgreSQL Connection Failed
Condition: postgres status = unreachable
Duration: 1 minute
Action: Page on-call engineer

Alert: Archival Job Failed
Condition: archive_job error count increases
Duration: 5 minutes
Action: Send to Slack + email
```

### Prometheus Recording Rules
```yaml
groups:
- name: ml_dashboard
  interval: 30s
  rules:
  - record: job:error_rate:5m
    expr: rate(error_count_total[5m]) / rate(request_count_total[5m])
  
  - record: job:p95_latency:5m
    expr: histogram_quantile(0.95, rate(latency_seconds_bucket[5m]))
  
  - record: job:predictions_per_user:daily
    expr: sum(predictions_count) by (date)
```

---

## 🔄 Backup & Disaster Recovery

### PostgreSQL Backups
```bash
# Daily backup (add to cron)
docker-compose exec postgres pg_dump -U mluser mldb > backup_$(date +%Y%m%d).sql

# Or use WAL archiving
# Add to PostgreSQL config:
archive_mode = on
archive_command = 'cp %p /backups/%f'

# Restore from backup
docker-compose exec postgres psql -U mluser mldb < backup_20260423.sql
```

### Grafana Dashboard Backups
```bash
# Export dashboard JSON
curl http://localhost:3001/api/dashboards/uid/abc123 \
  -H "Authorization: Bearer YOUR_API_TOKEN" > dashboard_backup.json

# Restore
curl -X POST http://localhost:3001/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @dashboard_backup.json
```

---

## 📈 Scaling Considerations

### Single Instance (Current)
- ✅ Handles ~100 requests/sec
- ✅ Sufficient for <10M predictions/month
- ✅ Easy to deploy

### Multi-Instance (Load Balancing)
```yaml
# Use nginx as load balancer
upstream fastapi {
  server fastapi1:8000;
  server fastapi2:8000;
  server fastapi3:8000;
}

server {
  listen 80;
  location / {
    proxy_pass http://fastapi;
  }
}
```

### Database Scaling
- **Read Replicas**: PostgreSQL streaming replication
- **Sharding**: Partition by user_id for massive scale
- **Archive Service**: Separate job runner for archival

---

## 🧪 Testing in Production

### Health Checks
```bash
# API health
curl -f http://localhost:8001/health || alert "API down"

# Database
curl -f http://localhost:8001/status | grep postgres || alert "DB down"

# All services
curl -f http://localhost:8001/status | grep healthy || alert "System degraded"
```

### Load Testing
```bash
# Install hey
go install github.com/rakyll/hey@latest

# Test prediction endpoint
hey -n 10000 -c 100 "http://localhost:8001/predict?text=test"

# Results: throughput, latency distribution, errors
```

---

## 📝 Maintenance Schedule

| Task | Frequency | Command |
|------|-----------|---------|
| PostgreSQL Backup | Daily | `docker-compose exec postgres pg_dump ...` |
| Archive Job | Daily | Automatic (configured in app.py) |
| Log Rotation | Weekly | `docker-compose logs --tail 1000 > archive.log` |
| Update Images | Monthly | `docker-compose pull && docker-compose up -d` |
| Security Patches | As needed | Review CVEs for base images |
| Database Vacuum | Weekly | `docker-compose exec postgres vacuum` |

---

## 🆘 Troubleshooting Production Issues

### Service down
```bash
# Check logs
docker-compose logs fastapi
docker-compose logs postgres
docker-compose logs grafana

# Restart service
docker-compose restart fastapi

# Full reset (careful!)
docker-compose down -v
docker-compose up -d
```

### Slow queries
```bash
# Enable query logging
docker-compose exec postgres psql -U mluser -d mldb
> SET log_min_duration_statement = 1000;

# Check slow query log
docker-compose logs postgres | grep duration
```

### PostgreSQL connection pool exhausted
```bash
# Increase max connections in docker-compose.yml
command: "-c max_connections=200"

# Or optimize connection pool in app
# Reduce pool_size in database.py
```

---

## 📞 Support & Documentation

- **API Docs**: http://localhost:8001/docs (FastAPI Swagger)
- **Prometheus**: http://localhost:9091
- **Grafana**: http://localhost:3001
- **GitHub**: https://github.com/your-org/ml-dashboard
- **Issues**: Open GitHub issue or contact team

