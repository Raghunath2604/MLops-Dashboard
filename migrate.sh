#!/bin/bash
# Migration runner script
# This script applies the multi-tenancy migration to your database

set -e

echo "======================================"
echo "Multi-Tenancy Migration Runner"
echo "======================================"
echo ""

# Check if database connection is available
echo "Step 1: Checking database connection..."

if ! psql "$DATABASE_URL" -c "SELECT 1" > /dev/null 2>&1; then
    echo "❌ Cannot connect to database"
    echo "Please set DATABASE_URL environment variable"
    echo "Example: export DATABASE_URL=postgresql://user:password@localhost/mldashboard"
    exit 1
fi

echo "✓ Database connection successful"
echo ""

# Run migration
echo "Step 2: Running multi-tenancy migration..."
echo "This will:"
echo "  - Create organization tables"
echo "  - Create API key tables"
echo "  - Add organization_id columns"
echo "  - Create default organization"
echo "  - Create subscription tiers"
echo ""

psql "$DATABASE_URL" -f migrations/001_add_multitenancy.sql

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Migration completed successfully!"
    echo ""
    echo "======================================"
    echo "Next steps:"
    echo "======================================"
    echo "1. Start the API: docker-compose up"
    echo "2. Run tests: python test_multitenancy.py"
    echo "3. Check the dashboard at: http://localhost:8000"
    echo ""
    echo "Example API usage:"
    echo "  curl -X POST http://localhost:8000/auth/register \\
    echo "    -d 'username=testuser&password=test123'"
    echo ""
else
    echo ""
    echo "❌ Migration failed!"
    echo "Please check the error messages above"
    exit 1
fi
