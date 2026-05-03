#!/bin/bash
# Quick Start Guide for Multi-Tenant Testing
# This script provides step-by-step commands to test the multi-tenant setup locally

set -e

echo "================================================"
echo "Multi-Tenant SaaS - Local Testing Quick Start"
echo "================================================"
echo ""

# Check prerequisites
echo "Step 1: Checking prerequisites..."
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi
echo "✓ Docker is installed"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi
echo "✓ Docker Compose is installed"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3 first."
    exit 1
fi
echo "✓ Python 3 is installed"

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo "⚠️  pip3 not found. Will attempt to install dependencies anyway."
fi

echo ""
echo "================================================"
echo "Step 2: Install Python dependencies"
echo "================================================"
echo ""

# Check if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip3 install -r requirements.txt
else
    echo "⚠️  requirements.txt not found"
    echo "Installing common dependencies..."
    pip3 install fastapi uvicorn sqlalchemy psycopg2-binary transformers prometheus-client python-jose cryptography \
                python-dotenv httpx
fi

echo ""
echo "================================================"
echo "Step 3: Start PostgreSQL"
echo "================================================"
echo ""

echo "Starting PostgreSQL container..."
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
RETRY_COUNT=0
MAX_RETRIES=30

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker-compose logs postgres | grep -q "ready to accept connections"; then
        echo "✓ PostgreSQL is ready"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ PostgreSQL failed to start"
    echo "Logs:"
    docker-compose logs postgres
    exit 1
fi

echo ""
echo "================================================"
echo "Step 4: Apply Database Migration"
echo "================================================"
echo ""

# Get database URL from .env or use default
if [ -f ".env" ]; then
    source .env
fi

DATABASE_URL="${DATABASE_URL:-postgresql://admin:admin_password@localhost:5432/mldashboard}"

echo "Using DATABASE_URL: $DATABASE_URL"
echo ""

# Check if migration file exists
if [ ! -f "migrations/001_add_multitenancy.sql" ]; then
    echo "❌ Migration file not found at migrations/001_add_multitenancy.sql"
    exit 1
fi

echo "Running migration..."
if psql "$DATABASE_URL" -f migrations/001_add_multitenancy.sql > /dev/null 2>&1; then
    echo "✓ Migration completed successfully"
else
    echo "❌ Migration failed"
    echo "Attempting to run migration with error output..."
    psql "$DATABASE_URL" -f migrations/001_add_multitenancy.sql
    exit 1
fi

echo ""
echo "================================================"
echo "Step 5: Verify Migration"
echo "================================================"
echo ""

TABLE_COUNT=$(psql "$DATABASE_URL" -t -c "
    SELECT COUNT(*) FROM information_schema.tables
    WHERE table_schema = 'public';
" | tr -d ' ')

echo "Created $TABLE_COUNT tables"
echo ""
echo "Key tables:"

psql "$DATABASE_URL" -t -c "
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name;
" | grep -E "organizations|api_keys|subscription|users|prediction" | sed 's/^/  - /'

echo ""
echo "✓ Migration verified"

echo ""
echo "================================================"
echo "Step 6: Start FastAPI Application"
echo "================================================"
echo ""

echo "Starting FastAPI application..."
echo "Building Docker image..."
docker build -t mldashboard:latest . > /dev/null 2>&1

echo "Starting containers..."
docker-compose up -d

# Wait for API to be ready
echo "Waiting for API to be ready..."
RETRY_COUNT=0
MAX_RETRIES=30

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        echo "✓ FastAPI is ready"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ FastAPI failed to start"
    echo "Logs:"
    docker-compose logs api
    exit 1
fi

echo ""
echo "================================================"
echo "Step 7: Run Multi-Tenant Test Suite"
echo "================================================"
echo ""

if [ ! -f "test_multitenancy.py" ]; then
    echo "❌ Test file not found at test_multitenancy.py"
    exit 1
fi

echo "Running test_multitenancy.py..."
echo ""

if python3 test_multitenancy.py; then
    echo ""
    echo "✅ ALL TESTS PASSED!"
else
    echo ""
    echo "❌ TESTS FAILED"
    echo ""
    echo "Debugging tips:"
    echo "1. Check API logs: docker-compose logs api"
    echo "2. Check database: psql \$DATABASE_URL -c 'SELECT * FROM organizations;'"
    echo "3. Verify middleware: Look for org_id extraction in logs"
    exit 1
fi

echo ""
echo "================================================"
echo "Step 8: Manual API Testing"
echo "================================================"
echo ""

echo "Testing user registration..."
REGISTER_RESPONSE=$(curl -s -X POST "http://localhost:8000/auth/register" \
  -d "username=manual_test_user&password=test123")

API_KEY=$(echo $REGISTER_RESPONSE | grep -o '"api_key":"[^"]*' | cut -d'"' -f4)

if [ -z "$API_KEY" ]; then
    echo "❌ Failed to get API key"
    echo "Response: $REGISTER_RESPONSE"
    exit 1
fi

echo "✓ User registered"
echo "  API Key: ${API_KEY:0:20}..."
echo ""

echo "Testing prediction endpoint..."
PREDICT_RESPONSE=$(curl -s -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/predict?text=This%20is%20amazing")

if echo $PREDICT_RESPONSE | grep -q "prediction"; then
    echo "✓ Prediction successful"
    echo "  Response: $PREDICT_RESPONSE"
else
    echo "❌ Prediction failed"
    echo "  Response: $PREDICT_RESPONSE"
    exit 1
fi

echo ""
echo "Testing predictions retrieval..."
PREDICTIONS_RESPONSE=$(curl -s -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/predictions")

if echo $PREDICTIONS_RESPONSE | grep -q "predictions"; then
    echo "✓ Retrieved predictions"
    COUNT=$(echo $PREDICTIONS_RESPONSE | grep -o '"total":[0-9]*' | cut -d':' -f2)
    echo "  Total predictions: $COUNT"
else
    echo "❌ Failed to retrieve predictions"
    exit 1
fi

echo ""
echo "================================================"
echo "✅ LOCAL TESTING COMPLETE!"
echo "================================================"
echo ""

echo "Summary:"
echo "  ✓ PostgreSQL running"
echo "  ✓ Migration applied"
echo "  ✓ FastAPI running"
echo "  ✓ Multi-tenant isolation verified"
echo "  ✓ Authentication working"
echo "  ✓ API endpoints responding"
echo ""

echo "Next steps:"
echo "1. View API documentation: http://localhost:8000/docs"
echo "2. Check logs: docker-compose logs -f api"
echo "3. View database: psql \$DATABASE_URL"
echo "4. Proceed to Phase 2: Rate limiting & Billing"
echo ""

echo "To stop everything:"
echo "  docker-compose down"
echo ""

echo "To reset and start over:"
echo "  docker-compose down -v"
echo "  bash migrate.sh"
echo "  docker-compose up"
echo ""
