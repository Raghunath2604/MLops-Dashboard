# ML Dashboard Test Script (PowerShell)
# Tests all endpoints including new PostgreSQL features

$BaseURL = "http://localhost:8001"

function Test-Endpoint {
    param(
        [string]$Method = "GET",
        [string]$Endpoint,
        [string]$Description,
        [object]$Body = $null
    )

    Write-Host "`n========================================" -ForegroundColor Yellow
    Write-Host $Description -ForegroundColor Cyan
    Write-Host $Endpoint -ForegroundColor Gray

    try {
        if ($Body) {
            $response = Invoke-WebRequest -Uri "$BaseURL$Endpoint" -Method $Method -Body $Body -ContentType "application/json" -UseBasicParsing
        } else {
            $response = Invoke-WebRequest -Uri "$BaseURL$Endpoint" -Method $Method -UseBasicParsing
        }

        Write-Host "✓ Status: $($response.StatusCode)" -ForegroundColor Green
        Write-Host $response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 3
    }
    catch {
        Write-Host "✗ Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Core Endpoints
Write-Host "`n######## ML DASHBOARD - TEST SUITE ########`n" -ForegroundColor Magenta

# 1. Health Check
Test-Endpoint -Endpoint "/health" -Description "1. Health Check"

# 2. Single Prediction
Test-Endpoint -Endpoint "/predict?text=This%20is%20amazing" -Description "2. Single Prediction"

# 3. Batch Predictions
$batchBody = @("Great product", "Terrible experience", "It's okay") | ConvertTo-Json
Test-Endpoint -Endpoint "/batch-predict" -Method "POST" -Body $batchBody -Description "3. Batch Predictions"

# 4. Status (includes PostgreSQL)
Test-Endpoint -Endpoint "/status" -Description "4. Service Status (with PostgreSQL)"

# 5. Drilldown Metrics
Test-Endpoint -Endpoint "/drilldown" -Description "5. Drilldown Metrics"

# 6. Prometheus Metrics
Test-Endpoint -Endpoint "/metrics" -Description "6. Prometheus Metrics"

# ============ NEW ENDPOINTS ============

# 7. Register User
Write-Host "`n### NEW ENDPOINTS - User Authentication & Data Persistence ###" -ForegroundColor Green
Test-Endpoint -Endpoint "/auth/register?username=testuser123" -Description "7. Register New User (get API key)"

# 8. Login
# Note: Replace API_KEY with the one from register response
Write-Host "`n[INFO] Use the API key from register response for login" -ForegroundColor Yellow
$testAPIKey = "test-api-key"
Test-Endpoint -Endpoint "/auth/login?username=testuser123&api_key=$testAPIKey" -Description "8. Login (get JWT token)" -Method "POST"

# 9. List Predictions
Test-Endpoint -Endpoint "/predictions?limit=10" -Description "9. List Predictions (from database)"

# 10. Query with Filters
Test-Endpoint -Endpoint "/predictions?limit=5&confidence_min=0.95&prediction_type=POSITIVE" -Description "10. Query Predictions with Filters"

# 11. Historical Statistics
Test-Endpoint -Endpoint "/predictions/stats" -Description "11. Historical Statistics (daily aggregates)"

# 12. Export to JSON
Test-Endpoint -Endpoint "/predictions/export?format=json" -Method "POST" -Description "12. Export Predictions (JSON)"

# 13. Export to CSV
Test-Endpoint -Endpoint "/predictions/export?format=csv" -Method "POST" -Description "13. Export Predictions (CSV)"

Write-Host "`n`n========== TEST COMPLETE ==========`n" -ForegroundColor Magenta
Write-Host "Grafana Dashboard: http://localhost:3001 (admin/admin)" -ForegroundColor Cyan
Write-Host "PostgreSQL: localhost:5432 (mluser/mlpassword)" -ForegroundColor Cyan
Write-Host "API Documentation: http://localhost:8001/docs" -ForegroundColor Cyan
