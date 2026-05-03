<div align="center">

# FinSight AI — MLOps Observability & SaaS Dashboard

**Enterprise-grade ML inference platform with real-time observability, multi-tenant SaaS billing, and a premium React dashboard — powered by BERT, FastAPI, and a full Prometheus/Grafana/Loki/Jaeger stack.**

[![Python](https://img.shields.io/badge/Python-3.10-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![Prometheus](https://img.shields.io/badge/Prometheus-Monitoring-E6522C?logo=prometheus&logoColor=white)](https://prometheus.io)
[![Grafana](https://img.shields.io/badge/Grafana-Dashboards-F46800?logo=grafana&logoColor=white)](https://grafana.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

<br/>

![Dashboard Overview](screenshots/dashboard-overview.png)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Screenshots](#-screenshots)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [Services & Ports](#-services--ports)
- [API Reference](#-api-reference)
- [Observability Pipeline](#-observability-pipeline)
- [Multi-Tenancy & Billing](#-multi-tenancy--billing)
- [Project Structure](#-project-structure)
- [Grafana Dashboards](#-grafana-dashboards)
- [Deployment](#-deployment)
- [Troubleshooting](#-troubleshooting)

---

## 🎯 Overview

**FinSight AI** is a production-ready MLOps platform that combines:

- 🧠 **BERT Sentiment Analysis** — Real-time NLP inference via HuggingFace DistilBERT
- 📊 **Full Observability Stack** — Prometheus metrics, Grafana dashboards, Loki logs, Jaeger traces
- 🏢 **Multi-Tenant SaaS** — Organization isolation, tiered subscriptions, API key management
- 💳 **Billing System** — Free / Pro / Business tiers with rate limiting and monthly quotas
- 🔐 **Clerk Authentication** — OAuth 2.0 (Google) with JWT-based API access
- 🖥️ **Premium React Dashboard** — Dark-themed bento-grid UI with real-time metrics

> **Status**: ✅ Production Ready — 10 containerized services, 15+ API endpoints, fully verified

---

## 📸 Screenshots

<table>
<tr>
<td width="50%">

**Login Page (Clerk OAuth)**
![Login Page](screenshots/login-page.png)

</td>
<td width="50%">

**Dashboard Overview**
![Dashboard](screenshots/dashboard-overview.png)

</td>
</tr>
<tr>
<td width="50%">

**Prometheus Targets (UP)**
![Prometheus](screenshots/prometheus-targets.png)

</td>
<td width="50%">

**Grafana Monitoring**
![Grafana](screenshots/grafana-dashboard.png)

</td>
</tr>
<tr>
<td width="50%">

**Jaeger Distributed Tracing**
![Jaeger](screenshots/jaeger-tracing.png)

</td>
<td width="50%">

**AlertManager**
![AlertManager](screenshots/alertmanager.png)

</td>
</tr>
</table>

---

## 🏗️ Architecture

```
                          ┌──────────────────────────────┐
                          │       React Frontend         │
                          │  (Clerk Auth · Bento Grid)   │
                          │        :5173 / :8001         │
                          └──────────┬───────────────────┘
                                     │ JWT Bearer Token
                          ┌──────────▼───────────────────┐
                          │  FastAPI + BERT Model (:8001)│
                          │  ├─ /predict (sentiment)     │
                          │  ├─ /batch-predict           │
                          │  ├─ /predictions (CRUD)      │
                          │  ├─ /billing/* (SaaS)        │
                          │  ├─ /auth/* (Clerk + API)    │
                          │  ├─ /metrics (Prometheus)    │
                          │  └─ /health                  │
                          └──┬────┬────┬────┬────┬───────┘
                             │    │    │    │    │
              ┌──────────────┘    │    │    │    └──────────────┐
              │                   │    │    │                   │
    ┌─────────▼──────┐  ┌────────▼────▼────▼──────┐  ┌────────▼────────┐
    │  PostgreSQL    │  │  Observability Layer    │  │   Redis Cache   │
    │  (:5432)       │  │                         │  │   (:6379)       │
    │  ├─ users      │  │  Prometheus → :9091     │  │  Rate Limiting  │
    │  ├─ orgs       │  │  Grafana    → :3001     │  │  Session Cache  │
    │  ├─ predictions│  │  Loki       → :3011     │  └─────────────────┘
    │  ├─ metrics    │  │  Promtail   (collector) │
    │  ├─ billing    │  │  Jaeger     → :16686    │
    │  └─ api_keys   │  │  AlertMgr   → :9093     │
    └────────────────┘  └─────────────────────────┘
```

### Data Flow

```
User Input → Clerk JWT → Rate Limiter → BERT Inference → PostgreSQL Storage
                                              │
                           ┌──────────────────┼──────────────────┐
                           │                  │                  │
                     Prometheus          Loki/Promtail       Jaeger
                     (metrics)           (app logs)         (traces)
                           │                  │                  │
                           └──────────┬───────┘                  │
                                      │                          │
                                   Grafana ◄─────────────────────┘
                                 (unified view)
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18 + Vite | Premium dark-themed SaaS dashboard |
| **Auth** | Clerk (OAuth 2.0) | Google SSO, JWT tokens, session management |
| **Backend** | FastAPI (Python 3.10) | Async REST API with 15+ endpoints |
| **ML Model** | DistilBERT (HuggingFace) | Sentiment analysis inference (~40ms) |
| **Database** | PostgreSQL 15 | Multi-tenant data storage with async SQLAlchemy |
| **Cache** | Redis 7 | Rate limiting, session caching |
| **Metrics** | Prometheus | Time-series metrics collection (15s scrape) |
| **Dashboards** | Grafana | Real-time visualization with 4 data sources |
| **Logs** | Loki + Promtail | Centralized log aggregation and search |
| **Tracing** | Jaeger + OpenTelemetry | Distributed request tracing |
| **Alerting** | AlertManager | Threshold-based alert routing |
| **Container** | Docker Compose | 10-service orchestration |

---

## 🚀 Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (v4.0+)
- [Node.js](https://nodejs.org/) (v18+ for frontend development)

### One-Command Launch

```bash
# Clone the repository
git clone https://github.com/Raghunath2604/MLops-Dashboard.git
cd MLops-Dashboard

# Start the full stack (10 containers)
docker-compose up --build -d

# Wait ~60 seconds for BERT model download on first run
```

### Windows Quick Start

```batch
run.bat
```

### Verify All Services

```bash
# API Health
curl http://localhost:8001/health
# → {"status": "healthy", "service": "BERT Sentiment Analysis API"}

# Prometheus Targets
curl http://localhost:9091/api/v1/targets
# → fastapi target: "health": "up"

# Grafana
open http://localhost:3001  # admin / admin
```

---

## 🌐 Services & Ports

| Service | Port | URL | Credentials |
|---------|------|-----|-------------|
| **FinSight Dashboard** | `8001` | http://localhost:8001 | Clerk OAuth |
| **FastAPI Docs** | `8001` | http://localhost:8001/docs | — |
| **Grafana** | `3001` | http://localhost:3001 | `admin` / `admin` |
| **Prometheus** | `9091` | http://localhost:9091 | — |
| **Jaeger UI** | `16686` | http://localhost:16686 | — |
| **AlertManager** | `9093` | http://localhost:9093 | — |
| **Loki** | `3011` | http://localhost:3011 | — |
| **PostgreSQL** | `5432` | `mluser` / `mlpassword` | DB: `mldb` |
| **Redis** | `6379` | — | — |

---

## 📡 API Reference

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register?username=&password=` | Register user, returns API key |
| `GET` | `/auth/my-key` | Generate new API key (JWT required) |

### ML Inference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/predict?text=...` | Single sentiment prediction |
| `POST` | `/batch-predict` | Batch predictions (JSON array) |

### Data & Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/predictions?limit=&offset=` | Query prediction history |
| `GET` | `/predictions/export?format=csv` | Export as CSV or JSON |
| `GET` | `/model-metrics` | Aggregated model performance |
| `GET` | `/sentiments` | Sentiment distribution |

### Billing & Subscriptions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/billing/subscription` | Current plan details |
| `POST` | `/billing/upgrade?tier_name=pro` | Upgrade subscription tier |

### Health & Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health check |
| `GET` | `/status` | Detailed status with DB health |
| `GET` | `/metrics` | Prometheus metrics (scrape target) |

### Example Usage

```bash
# 1. Register a user
curl -X POST "http://localhost:8001/auth/register?username=demo&password=secret"
# → {"username": "demo", "api_key": "RvmMR...", "organization": "demo-ba0f8f73"}

# 2. Make a prediction
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "http://localhost:8001/predict?text=This+product+is+amazing"
# → {"prediction": "POSITIVE", "confidence": 0.9998, "inference_time_ms": 42.3}

# 3. Batch predict
curl -X POST -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '["Great service!", "Terrible experience", "Its okay"]' \
     http://localhost:8001/batch-predict
```

---

## 📊 Observability Pipeline

### Prometheus → Grafana (Metrics)

FastAPI exposes `/metrics` in Prometheus format. Prometheus scrapes every **15 seconds**.

```promql
# Request rate (req/sec)
rate(request_count_total[1m])

# Error rate (%)
(rate(error_count_total[1m]) / rate(request_count_total[1m])) * 100

# P95 Latency
histogram_quantile(0.95, rate(latency_seconds_bucket[1m]))
```

### Promtail → Loki → Grafana (Logs)

Application logs are written to `app.log`, collected by Promtail, and pushed to Loki.

```logql
# All application logs
{job="model_logs"}

# Filter for errors
{job="model_logs"} |= "ERROR"

# Prediction events
{job="model_logs"} |= "Prediction Success"
```

### OpenTelemetry → Jaeger (Traces)

Every API request is automatically instrumented with distributed tracing spans.

- **FastAPI** instrumented via `FastAPIInstrumentor`
- **SQLAlchemy** instrumented via `SQLAlchemyInstrumentor`
- **HTTP** calls instrumented via `RequestsInstrumentor`

### AlertManager (Alerting)

Prometheus alert rules fire to AlertManager when thresholds are breached.

```yaml
# Alert when error rate exceeds 5%
- alert: HighErrorRate
  expr: rate(error_count_total[5m]) / rate(request_count_total[5m]) > 0.05
  for: 5m
```

---

## 🏢 Multi-Tenancy & Billing

### Organization Isolation

Every user belongs to an **Organization**. All data (predictions, metrics, API keys) is scoped to the organization level, ensuring complete tenant isolation.

### Subscription Tiers

| Tier | Price | Requests/Month | Rate Limit | Batch Size |
|------|-------|----------------|------------|------------|
| **Free** | $0 | 10,000 | 10 req/min | 100 |
| **Pro** | $29 | 100,000 | 100 req/min | 1,000 |
| **Business** | $299 | 1,000,000 | 500 req/min | 10,000 |

### Rate Limiting

Requests are rate-limited per organization based on their subscription tier. When exceeded, the API returns `429 Too Many Requests` with a `Retry-After` header.

---

## 📁 Project Structure

```
mldashborad/
├── app.py                          # FastAPI application (15+ endpoints)
├── auth.py                         # Clerk JWT + API key authentication
├── models.py                       # SQLAlchemy ORM (7 models)
├── database.py                     # Async PostgreSQL connection
├── billing.py                      # Stripe integration & tier logic
├── rate_limiter.py                 # Per-org rate limiting engine
├── archive_job.py                  # 90-day data retention scheduler
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Multi-stage build (Node + Python)
├── docker-compose.yml              # 10-service orchestration
│
├── prometheus.yml                  # Scrape config → fastapi:8000
├── alert-rules.yml                 # Alert thresholds
├── alertmanager.yml                # Alert routing config
├── loki-config.yaml                # Loki storage backend
├── promtail-config.yaml            # Log collector → Loki
├── grafana-datasources.yml         # Auto-provisioned data sources
├── grafana-dashboard.json          # Pre-built dashboard panels
│
├── frontend/                       # React 18 + Vite
│   ├── src/
│   │   ├── App.jsx                 # Main SaaS dashboard component
│   │   ├── main.jsx                # Clerk provider setup
│   │   └── index.css               # Premium dark theme (600+ lines)
│   ├── .env.production             # Clerk keys & routing
│   └── package.json
│
├── screenshots/                    # Documentation images
├── .github/workflows/deploy.yml    # CI/CD pipeline
└── README.md                       # This file
```

---

## 📊 Grafana Dashboards

### Auto-Configured Data Sources

All data sources are provisioned automatically via `grafana-datasources.yml`:

| Source | Type | Internal URL |
|--------|------|-------------|
| Prometheus | Metrics | `http://prometheus:9090` |
| Loki | Logs | `http://loki:3100` |
| Jaeger | Traces | `http://jaeger:16686` |
| AlertManager | Alerts | `http://alertmanager:9093` |

### Import Pre-Built Dashboard

1. Open **Grafana** → http://localhost:3001
2. Login with `admin` / `admin`
3. Navigate to **Dashboards** → **Import**
4. Upload `grafana-dashboard.json`
5. Select the Prometheus data source → **Import**

**Included panels:** Request Rate · Error Rate · Average Latency · Sentiment Distribution · Recent Predictions · Predictions Over Time · Confidence Histogram

---

## ☁️ Deployment

### AWS EC2 (Recommended)

The project ships with a ready-to-use deployment script:

```bash
# 1. Launch a t3.large EC2 instance (Ubuntu 22.04)
# 2. Upload your code or use S3
# 3. Run the stack
docker-compose up --build -d
```

**Required Security Group Ports:** `8001`, `3001`, `9091`, `16686`, `9093`

### Environment Variables

```env
# Backend (.env)
DATABASE_URL=postgresql+asyncpg://mluser:mlpassword@postgres:5432/mldb
REDIS_URL=redis://redis:6379
JAEGER_HOST=jaeger
JAEGER_PORT=6831

# Frontend (frontend/.env.production)
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...
VITE_CLERK_SIGN_IN_URL=/sign-in
VITE_CLERK_SIGN_UP_URL=/sign-up
VITE_CLERK_AFTER_SIGN_IN_URL=/dashboard
VITE_CLERK_AFTER_SIGN_UP_URL=/dashboard
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| Containers not starting | Run `docker-compose logs` to check errors |
| Can't access Grafana | Wait 30s after startup, check `docker-compose ps` |
| No metrics in Grafana | Send a few requests first, wait 15s for scrape |
| Clerk login redirect error | Add your domain to Clerk Dashboard → Redirect URLs |
| Database column missing | Run `docker exec postgres_db psql -U mluser -d mldb -c "..."` |
| Model download slow | First startup downloads ~250MB BERT model, be patient |

---

## 🎓 Technical Highlights (Resume / Interview)

| # | Achievement |
|---|-------------|
| 1 | Deployed BERT sentiment analysis as a production REST API with <50ms inference |
| 2 | Built a full observability pipeline: Prometheus + Grafana + Loki + Jaeger |
| 3 | Implemented multi-tenant SaaS architecture with organization-level data isolation |
| 4 | Designed tiered billing system with per-org rate limiting and monthly quotas |
| 5 | Integrated Clerk OAuth 2.0 authentication with JWT-based API access |
| 6 | Created premium React dashboard with real-time bento-grid metrics visualization |
| 7 | Orchestrated 10 containerized microservices via Docker Compose |
| 8 | Implemented distributed tracing with OpenTelemetry + Jaeger instrumentation |
| 9 | Built async PostgreSQL storage with SQLAlchemy ORM and 90-day data retention |
| 10 | Configured AlertManager with threshold-based alerting rules |

---

<div align="center">

**Built with ❤️ by [Raghunath](https://github.com/Raghunath2604)**

[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)]()
[![Services](https://img.shields.io/badge/Services-10%2F10%20Running-blue)]()
[![Endpoints](https://img.shields.io/badge/API%20Endpoints-15+-orange)]()

**Last Updated**: May 2026 · **Version**: 4.0 (SaaS Edition)

</div>
