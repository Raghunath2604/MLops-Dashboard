# 🚀 Zenith MLOps: The Ultimate AI SaaS Platform

A professional, enterprise-grade MLOps platform for sentiment analysis and toxicity detection. Built with a full-loop engineering approach, featuring automated drift detection, human-in-the-loop labeling, and self-improving model orchestration.

## 🌟 Key Features

- **🧠 Multi-Model Intelligence:** Real-time BERT sentiment and toxicity detection.
- **⚡ Optimal Performance:** Semantic caching with Redis for sub-1ms repeat inference.
- **👁️ Human-in-the-Loop (HITL):** Low-confidence data flagged for human review and labeling.
- **🚀 Automated Retraining:** One-click model versioning and self-improvement loops.
- **📊 Zenith Analytics:** Hourly drift visualization and enterprise audit trails.
- **🛠️ Developer Portal:** Stripe-style interactive docs with live API execution.
- **🔒 Enterprise Security:** Multi-tenant isolation, Clerk auth, and secure audit logging.
- **📈 Observability:** Full stack with Prometheus, Grafana, Loki, and Jaeger.

## 🏗️ Architecture

The platform is 100% containerized and designed for high-availability.

- **Backend:** FastAPI, BERT (Hugging Face), PostgreSQL, Redis.
- **Frontend:** React, Recharts, Clerk Auth.
- **Monitoring:** Prometheus (Metrics), Grafana (Visualization), Loki (Logs), Jaeger (Tracing), Alertmanager (Email).
- **Billing:** Stripe-ready multi-tenant subscription tiers.

## 🚦 Getting Started

### 1. Prerequisites
- Docker & Docker Compose
- Clerk API Keys (for Authentication)

### 2. Environment Setup
Create a `.env` file in the root:
```env
CLERK_SECRET_KEY=your_clerk_secret
CLERK_PUBLISHABLE_KEY=your_clerk_pub
DATABASE_URL=postgresql+asyncpg://mluser:mlpassword@postgres:5432/mldb
REDIS_URL=redis://redis:6379
```

### 3. Launch the Platform
```bash
docker-compose up -d --build
```

### 4. Access the Services
- **User Dashboard:** `http://localhost:8001`
- **Model Metrics (Grafana):** `http://localhost:3001`
- **Distributed Traces (Jaeger):** `http://localhost:16686`
- **System Logs (Loki):** `http://localhost:3011`

## 💎 Zenith Level Engineering
This project implements the "Full-Loop" MLOps philosophy:
`Inference -> Drift Detection -> Alerting -> Human Review -> Retraining -> Version Bump`

---
Built with ❤️ for the future of AI Engineering.
