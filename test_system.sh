#!/bin/bash

echo "===== COMPREHENSIVE SYSTEM TEST ====="
echo ""

# Test 1: API Health
echo "1. Testing API Health..."
curl -s http://localhost:8001/health | jq . && echo "✅ API Health OK" || echo "❌ API Health FAILED"
echo ""

# Test 2: Single Prediction
echo "2. Testing Single Prediction..."
curl -s "http://localhost:8001/predict?text=This%20is%20amazing" | jq . && echo "✅ Single Prediction OK" || echo "❌ Single Prediction FAILED"
echo ""

# Test 3: Batch Prediction
echo "3. Testing Batch Prediction..."
curl -s -X POST http://localhost:8001/batch-predict \
  -H "Content-Type: application/json" \
  -d '["Great product", "Terrible experience", "Its okay"]' | jq . && echo "✅ Batch Prediction OK" || echo "❌ Batch Prediction FAILED"
echo ""

# Test 4: Drilldown Metrics
echo "4. Testing Drilldown Metrics..."
curl -s http://localhost:8001/drilldown | jq . && echo "✅ Drilldown OK" || echo "❌ Drilldown FAILED"
echo ""

# Test 5: Status Check
echo "5. Testing Status Check..."
curl -s http://localhost:8001/status | jq . && echo "✅ Status OK" || echo "❌ Status FAILED"
echo ""

# Test 6: Prometheus Connectivity
echo "6. Testing Prometheus..."
curl -s http://localhost:9091/-/healthy && echo "✅ Prometheus OK" || echo "❌ Prometheus FAILED"
echo ""

# Test 7: Loki Connectivity
echo "7. Testing Loki..."
curl -s http://localhost:3011/ready && echo "✅ Loki OK" || echo "❌ Loki FAILED"
echo ""

# Test 8: Grafana Connectivity
echo "8. Testing Grafana..."
curl -s http://localhost:3001/api/health | jq . && echo "✅ Grafana OK" || echo "❌ Grafana FAILED"
echo ""

echo "===== TEST COMPLETE ====="
