# Grafana + PostgreSQL Dashboard Setup

## Step 1: Access Grafana
```
URL: http://localhost:3001
Username: admin
Password: admin
```

## Step 2: Verify PostgreSQL Data Source
1. Go to **Configuration → Data Sources**
2. Look for **PostgreSQL** (should be auto-added)
3. Click it → Click **Test** button
4. Should show **"Database Connection OK"**

## Step 3: Create Dashboard

### Panel 1: Prediction Count Over Time
```sql
SELECT
  DATE(timestamp) as time,
  COUNT(*) as predictions
FROM prediction_records
WHERE archived = FALSE
GROUP BY DATE(timestamp)
ORDER BY time DESC
```
- **Chart Type**: Time series
- **Title**: Predictions Over Time
- **Format**: Graph with time on X-axis

### Panel 2: Confidence Distribution
```sql
SELECT
  ROUND(confidence * 100) as confidence_bucket,
  COUNT(*) as count
FROM prediction_records
WHERE archived = FALSE
GROUP BY ROUND(confidence * 100)
ORDER BY confidence_bucket
```
- **Chart Type**: Bar chart
- **Title**: Confidence Distribution

### Panel 3: Sentiment Distribution (Pie Chart)
```sql
SELECT
  prediction,
  COUNT(*) as count
FROM prediction_records
WHERE archived = FALSE
GROUP BY prediction
```
- **Chart Type**: Pie chart
- **Title**: POSITIVE vs NEGATIVE Predictions

### Panel 4: Average Inference Time by Day
```sql
SELECT
  DATE(timestamp) as day,
  ROUND(AVG(inference_time_ms)::numeric, 2) as avg_inference_ms
FROM prediction_records
WHERE archived = FALSE
GROUP BY DATE(timestamp)
ORDER BY day DESC
LIMIT 30
```
- **Chart Type**: Time series
- **Title**: Avg Inference Time (ms)

### Panel 5: Top Recent Predictions (Table)
```sql
SELECT
  id,
  input_text,
  prediction,
  ROUND(confidence::numeric, 4) as confidence,
  ROUND(inference_time_ms::numeric, 2) as inference_ms,
  timestamp
FROM prediction_records
WHERE archived = FALSE
ORDER BY timestamp DESC
LIMIT 50
```
- **Chart Type**: Table
- **Title**: Recent Predictions

### Panel 6: User Analytics
```sql
SELECT
  u.username,
  COUNT(pr.id) as total_predictions,
  ROUND(AVG(pr.confidence)::numeric, 4) as avg_confidence,
  ROUND(AVG(pr.inference_time_ms)::numeric, 2) as avg_inference_ms
FROM users u
LEFT JOIN prediction_records pr ON u.id = pr.user_id
GROUP BY u.username
ORDER BY total_predictions DESC
```
- **Chart Type**: Table
- **Title**: User Analytics

---

## How to Add a Panel

1. Click **+ Add Panel**
2. Select **PostgreSQL** as data source
3. Paste SQL query from above
4. Choose visualization type
5. Click **Apply**

---

## SQL Queries Reference

### Get all prediction data
```sql
SELECT * FROM prediction_records LIMIT 100;
```

### Get daily statistics
```sql
SELECT * FROM model_metrics ORDER BY date DESC;
```

### Get user stats
```sql
SELECT u.username, COUNT(pr.id) as predictions
FROM users u
LEFT JOIN prediction_records pr ON u.id = pr.user_id
GROUP BY u.username;
```

### Count archived vs active
```sql
SELECT
  archived,
  COUNT(*) as count
FROM prediction_records
GROUP BY archived;
```

### Predictions by sentiment
```sql
SELECT
  prediction,
  COUNT(*) as count,
  ROUND(AVG(confidence)::numeric, 4) as avg_confidence
FROM prediction_records
WHERE archived = FALSE
GROUP BY prediction;
```

---

## Now You Have:

✅ **3 Data Sources in Grafana:**
- Prometheus (metrics)
- Loki (logs)
- PostgreSQL (predictions data)

✅ **Visualize:**
- Real-time API metrics
- Application logs
- Historical predictions
- User analytics
- Performance trends

✅ **Full Observability:**
- What happened (Logs)
- How fast (Metrics)
- What was predicted (Database)
