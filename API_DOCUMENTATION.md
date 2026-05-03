# BERT Sentiment Analysis API - Complete Documentation

## Base URL
```
https://api.my-app.com  (Production)
http://localhost:8000   (Local Development)
```

## Authentication

All endpoints except `/health` and `/metrics` require authentication using an API key.

### API Key
- Generated on user registration
- Passed in `Authorization: Bearer <API_KEY>` header
- Each organization has its own API key
- Scoped to organization data only

### Example Request
```bash
curl -H "Authorization: Bearer sk_test_1234567890abcdef" \
  https://api.my-app.com/predict?text=Hello
```

---

## Rate Limiting & Quotas

### Response Headers
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1620000000
X-Quota-Used: 150
X-Quota-Limit: 10000
X-Quota-Reset: 2024-06-01
```

### Tier-Based Limits

| Tier | Requests/Min | Requests/Month | Batch Size | Price |
|------|-------------|----------------|-----------|-------|
| Free | 10 | 10,000 | 50 | $0 |
| Pro | 100 | 100,000 | 1,000 | $29 |
| Business | 500 | 1,000,000 | 50,000 | $299 |
| Enterprise | 10,000 | Unlimited | Unlimited | Custom |

### Rate Limit Exceeded Response (429)
```json
{
  "error": "Rate limit exceeded",
  "limit": 100,
  "current": 100,
  "remaining": 0,
  "retry_after": 12
}
```

---

## Endpoints

### Public Endpoints (No Auth Required)

#### GET /
**Health & Info**
```bash
curl http://localhost:8000/
```

Response:
```json
{
  "message": "BERT Sentiment Analysis API Running",
  "model": "distilbert-base-uncased-finetuned-sst-2-english"
}
```

#### GET /health
**Service Health Check**
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "service": "BERT Sentiment Analysis API"
}
```

#### GET /metrics
**Prometheus Metrics**
```bash
curl http://localhost:8000/metrics
```

Returns Prometheus-formatted metrics for monitoring.

---

### Prediction Endpoints (Auth Required)

#### GET /predict
**Single Prediction**

```bash
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/predict?text=This%20product%20is%20amazing"
```

Parameters:
- `text` (required, string): Text to analyze

Response:
```json
{
  "input_text": "This product is amazing",
  "prediction": "POSITIVE",
  "confidence": 0.9987,
  "inference_time_ms": 45.23
}
```

Error: 401 (No API key), 429 (Rate limit exceeded)

---

#### POST /batch-predict
**Batch Predictions**

```bash
curl -X POST \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Great!", "Terrible", "Average"]}' \
  http://localhost:8000/batch-predict
```

Request Body:
```json
{
  "texts": ["Great!", "Terrible", "Average"]
}
```

Response:
```json
{
  "results": [
    {
      "input_text": "Great!",
      "prediction": "POSITIVE",
      "confidence": 0.9865
    },
    {
      "input_text": "Terrible",
      "prediction": "NEGATIVE",
      "confidence": 0.9921
    },
    {
      "input_text": "Average",
      "prediction": "POSITIVE",
      "confidence": 0.5123
    }
  ],
  "count": 3
}
```

Limit: 50 items (free tier), 1,000 (pro), 50,000 (business)

---

#### GET /predictions
**Get Prediction History**

```bash
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/predictions?limit=10"
```

Parameters:
- `limit` (optional, integer): Max 100 results, default 10

Response:
```json
{
  "predictions": [
    {
      "id": 1,
      "user_id": 42,
      "input_text": "Amazing product",
      "prediction": "POSITIVE",
      "confidence": 0.9987,
      "inference_time_ms": 45.23,
      "timestamp": "2024-05-03T10:30:00"
    }
  ],
  "total": 1
}
```

---

#### GET /predictions/export
**Export Predictions**

```bash
# JSON Export
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/predictions/export?format=json" \
  -o predictions.json

# CSV Export
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/predictions/export?format=csv" \
  -o predictions.csv
```

Parameters:
- `format` (optional): "json" or "csv", default "json"

Response: File download (attachment)

---

#### GET /status
**Org Status**

```bash
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/status
```

Response:
```json
{
  "status": "running",
  "total_predictions": 42,
  "model": "distilbert-base-uncased-finetuned-sst-2-english"
}
```

---

#### GET /sentiments
**Sentiment Distribution**

```bash
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/sentiments
```

Response:
```json
{
  "sentiments": {
    "POSITIVE": 28,
    "NEGATIVE": 14
  }
}
```

---

#### GET /model-metrics
**Performance Metrics**

```bash
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/model-metrics
```

Response:
```json
{
  "total": 42,
  "avg_confidence": 0.9543,
  "avg_inference_time_ms": 42.15
}
```

---

### Authentication Endpoints

#### POST /auth/register
**Create New Account**

```bash
curl -X POST \
  -d "username=john_doe&password=securepassword123" \
  http://localhost:8000/auth/register
```

Request:
- `username` (required, string): Unique username
- `password` (required, string): Password (stored hashed)

Response:
```json
{
  "username": "john_doe",
  "api_key": "sk_test_abcdef1234567890abcdef1234567890",
  "organization": "john_doe-xyz123"
}
```

**Save the API key!** You'll need it for all authenticated requests.

---

### Billing Endpoints (Auth Required)

#### GET /billing/subscription
**Current Subscription**

```bash
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/billing/subscription
```

Response:
```json
{
  "subscription_id": 1,
  "tier": "pro",
  "status": "active",
  "price_usd": 2900,
  "requests_per_month": 100000,
  "batch_limit": 1000,
  "rate_limit_rpm": 100,
  "usage": 15234,
  "remaining": 84766,
  "reset_date": "2024-06-01T00:00:00",
  "billing_cycle_start": "2024-05-01T00:00:00",
  "billing_cycle_end": "2024-06-01T00:00:00"
}
```

---

#### POST /billing/upgrade
**Upgrade Plan**

```bash
curl -X POST \
  -H "Authorization: Bearer $API_KEY" \
  -d "tier_name=business" \
  http://localhost:8000/billing/upgrade
```

Request:
- `tier_name` (required): "free", "pro", "business", "enterprise"

Response:
```json
{
  "status": "success",
  "tier": "business",
  "new_requests_per_month": 1000000,
  "message": "Successfully upgraded to business tier"
}
```

---

#### GET /billing/usage
**Detailed Usage Statistics**

```bash
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/billing/usage
```

Response:
```json
{
  "organization": "Acme Corp",
  "tier": "pro",
  "usage_this_month": 45231,
  "quota_limit": 100000,
  "remaining": 54769,
  "percentage_used": 45.23,
  "reset_date": "2024-06-01T00:00:00",
  "total_predictions_all_time": 342890,
  "average_confidence": 0.9632,
  "average_inference_time_ms": 41.28
}
```

---

#### POST /billing/webhook
**Stripe Webhooks**

```bash
# This is called by Stripe, not by you
# Stripe sends events to this endpoint
curl -X POST \
  -H "Content-Type: application/json" \
  -d @stripe_event.json \
  https://api.my-app.com/billing/webhook
```

Handled Events:
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_succeeded`
- `invoice.payment_failed`

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "Invalid parameter",
  "details": "text parameter is required"
}
```

### 401 Unauthorized
```json
{
  "error": "API key required"
}
```

### 429 Too Many Requests
```json
{
  "error": "Rate limit exceeded",
  "retry_after": 12,
  "reset_at": 1620000012
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## Code Examples

### Python
```python
import requests

API_KEY = "sk_test_..."
BASE_URL = "http://localhost:8000"

headers = {"Authorization": f"Bearer {API_KEY}"}

# Single prediction
response = requests.get(
    f"{BASE_URL}/predict",
    params={"text": "Amazing product!"},
    headers=headers
)
print(response.json())

# Batch prediction
data = {
    "texts": ["Great", "Terrible", "Average"]
}
response = requests.post(
    f"{BASE_URL}/batch-predict",
    json=data,
    headers=headers
)
print(response.json())
```

### JavaScript/Node.js
```javascript
const API_KEY = "sk_test_...";
const BASE_URL = "http://localhost:8000";

const headers = {
  "Authorization": `Bearer ${API_KEY}`,
  "Content-Type": "application/json"
};

// Single prediction
const result = await fetch(
  `${BASE_URL}/predict?text=Amazing`,
  { headers }
);
const data = await result.json();
console.log(data);

// Batch prediction
const batchResult = await fetch(
  `${BASE_URL}/batch-predict`,
  {
    method: "POST",
    headers,
    body: JSON.stringify({
      texts: ["Great", "Terrible", "Average"]
    })
  }
);
const batchData = await batchResult.json();
console.log(batchData);
```

### cURL
```bash
#!/bin/bash

API_KEY="sk_test_..."
BASE_URL="http://localhost:8000"

# Register
REGISTER=$(curl -X POST \
  -d "username=testuser&password=test123" \
  "$BASE_URL/auth/register")

API_KEY=$(echo $REGISTER | jq -r '.api_key')
echo "API Key: $API_KEY"

# Make prediction
curl -H "Authorization: Bearer $API_KEY" \
  "$BASE_URL/predict?text=Hello%20World"

# Get predictions
curl -H "Authorization: Bearer $API_KEY" \
  "$BASE_URL/predictions"

# Get usage
curl -H "Authorization: Bearer $API_KEY" \
  "$BASE_URL/billing/usage"
```

---

## Monitoring & Observability

### Prometheus Metrics
- `request_count` - Total requests
- `error_count` - Total errors
- `latency_seconds` - Request latency histogram

### OpenTelemetry Tracing
- Traces available at Jaeger UI: http://localhost:16686
- Full request tracing through FastAPI, SQLAlchemy, HTTP calls

### Logs
- Centralized in Grafana Loki
- View at: http://localhost:3011/explore
- Available in Grafana dashboard

---

## Compliance & SLA

### Uptime SLA
- Free: Best effort
- Pro: 99.5%
- Business: 99.9%
- Enterprise: 99.99%

### Data Retention
- Free: 30 days
- Pro: 90 days
- Business: 1 year
- Enterprise: Custom

### Support
- Free: Community (Slack)
- Pro: Email (24 hours)
- Business: Priority (4 hours)
- Enterprise: Dedicated account manager

---

## Changelog

### v1.0.0 (Current)
- ✅ Multi-tenant architecture
- ✅ API key authentication
- ✅ Rate limiting (per-minute & monthly)
- ✅ Subscription tiers (free/pro/business/enterprise)
- ✅ Stripe billing integration
- ✅ Batch predictions
- ✅ Data export (JSON/CSV)
- ✅ OpenTelemetry tracing
- ✅ Prometheus metrics

### v2.0.0 (Planned)
- Fine-tuning endpoint
- Custom models
- Advanced analytics dashboard
- Webhook events
- Audit logs
- IP whitelisting

---

## Support

- **Documentation**: https://docs.my-app.com
- **Email**: support@my-app.com
- **Slack**: https://slack.my-app.com
- **Status**: https://status.my-app.com

