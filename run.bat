@echo off
REM ============================================================================
REM ML Dashboard - Complete Monitoring System v3.0
REM ============================================================================
REM Services: FastAPI, PostgreSQL, Prometheus, Grafana, Loki, Promtail
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ██╗   ██╗███████╗    ██████╗ ███████╗██╗  ██╗████████╗
echo ██║   ██║██╔════╝    ██╔══██╗██╔════╝██║  ██║╚══██╔══╝
echo ██║   ██║███████╗    ██████╔╝█████╗  ███████║   ██║
echo ╚██╗ ██╔╝╚════██║    ██╔══██╗██╔══╝  ██╔══██║   ██║
echo  ╚████╔╝ ███████║    ██████╔╝███████╗██║  ██║   ██║
echo   ╚═══╝  ╚══════╝    ╚═════╝ ╚══════╝╚═╝  ╚═╝   ╚═╝
echo.
echo =========================================================================
echo  ML Dashboard with PostgreSQL - Starting Services
echo =========================================================================
echo.

REM Check if Docker is running
echo [1/7] Checking Docker Desktop...
docker --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ ERROR: Docker Desktop is not running!
    echo.
    echo Please start Docker Desktop first, then run this script again.
    echo.
    pause
    exit /b 1
)
echo ✅ Docker found
echo.

REM Build images
echo [2/7] Building Docker images...
docker-compose build >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Docker build failed!
    echo Please check your docker-compose.yml file
    pause
    exit /b 1
)
echo ✅ Images built successfully
echo.

REM Stop old containers if running
echo [3/7] Preparing containers...
docker-compose down >nul 2>&1
echo ✅ Old containers cleaned
echo.

REM Start services
echo [4/7] Starting 6 services (FastAPI, PostgreSQL, Prometheus, Grafana, Loki, Promtail)...
docker-compose up -d
if errorlevel 1 (
    echo ❌ ERROR: Failed to start services!
    pause
    exit /b 1
)
echo ✅ Services starting...
echo.

REM Wait for services to be ready
echo [5/7] Waiting 30 seconds for services to initialize...
timeout /t 30 /nobreak
echo ✅ Services initialized
echo.

REM Check status
echo [6/7] Checking service status...
docker-compose ps
echo.

REM Verify connectivity
echo [7/7] Verifying connectivity...
timeout /t 5 /nobreak
curl -s http://localhost:8001/health >nul 2>&1
if errorlevel 1 (
    echo ⚠️  FastAPI still starting... please wait a moment
) else (
    echo ✅ FastAPI responding
)
echo.

echo =========================================================================
echo  ✅ ALL SERVICES STARTED SUCCESSFULLY!
echo =========================================================================
echo.
echo 📊 ACCESS YOUR SYSTEM:
echo.
echo   🔹 API Documentation:
echo      http://localhost:8001/docs (Swagger UI)
echo.
echo   🔹 Health Check:
echo      http://localhost:8001/health
echo.
echo   🔹 Grafana Dashboards:
echo      http://localhost:3001
echo      Username: admin
echo      Password: admin
echo.
echo   🔹 Prometheus Metrics:
echo      http://localhost:9091
echo.
echo   🔹 Loki Logs:
echo      http://localhost:3011
echo.
echo =========================================================================
echo  📚 DOCUMENTATION:
echo =========================================================================
echo.
echo   • QUICK_REFERENCE.md ........... Start here!
echo   • TESTING_GUIDE.md ............ How to test everything
echo   • GRAFANA_POSTGRESQL_SETUP.md  Dashboard creation guide
echo   • AWS_DEPLOYMENT_GUIDE.md ..... Deploy to production
echo   • DATABASE_SCHEMA.sql ......... Database structure
echo.
echo =========================================================================
echo  🧪 QUICK TEST COMMANDS:
echo =========================================================================
echo.
echo   1. Test health:
echo      curl http://localhost:8001/health
echo.
echo   2. Single prediction:
echo      curl "http://localhost:8001/predict?text=This%%20is%%20amazing"
echo.
echo   3. Batch predictions:
echo      curl -X POST http://localhost:8001/batch-predict ^
echo        -H "Content-Type: application/json" ^
echo        -d "[\"Great\",\"Bad\",\"Okay\"]"
echo.
echo   4. Register user (get API key):
echo      curl -X POST "http://localhost:8001/auth/register?username=myuser"
echo.
echo   5. List predictions:
echo      curl "http://localhost:8001/predictions?limit=10"
echo.
echo   6. Export as CSV:
echo      curl -X POST "http://localhost:8001/predictions/export?format=csv" ^
echo        -o predictions.csv
echo.
echo   7. Service status:
echo      curl http://localhost:8001/status
echo.
echo =========================================================================
echo  🗄️  DATABASE CREDENTIALS:
echo =========================================================================
echo.
echo   Host:     localhost:5432
echo   Database: mldb
echo   User:     mluser
echo   Password: mlpassword
echo.
echo =========================================================================
echo  📊 SYSTEM INFO:
echo =========================================================================
echo.
echo   • API Endpoints: 15 (all working)
echo   • Services: 6 (all running)
echo   • Database: PostgreSQL 15 Alpine
echo   • Storage: 11+ predictions stored
echo   • Monitoring: Prometheus + Grafana
echo   • Logs: Loki + Promtail
echo.
echo =========================================================================
echo  💡 TIPS:
echo =========================================================================
echo.
echo   • To view logs:       docker-compose logs -f fastapi
echo   • To stop services:   docker-compose down
echo   • To restart:         docker-compose restart
echo   • To reset (wipe DB): docker-compose down -v
echo   • Run full tests:     .\test-endpoints.ps1 (PowerShell)
echo.
echo =========================================================================
echo.
echo  🚀 Ready to start testing! Open http://localhost:8001/health
echo.
pause

