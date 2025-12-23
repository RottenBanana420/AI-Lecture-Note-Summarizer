#!/bin/bash

# PostgreSQL Database Verification Script
# This script verifies that PostgreSQL and pgvector are properly configured

set -e

echo "🔍 PostgreSQL Database Verification"
echo "===================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to backend directory
cd "$BACKEND_DIR"

# Check if container is running
if ! docker-compose ps postgres | grep -q "Up"; then
    echo "❌ PostgreSQL container is not running!"
    echo "Start it with:"
    echo "  $SCRIPT_DIR/start-db.sh"
    exit 1
fi

echo "✅ Docker is running"
echo "✅ PostgreSQL container is running"
echo ""

# Test database connection
echo "🔌 Testing database connection..."
if docker-compose exec -T postgres psql -U postgres -d lecture_summarizer_dev -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✅ Database connection successful"
else
    echo "❌ Failed to connect to database"
    exit 1
fi

# Check pgvector extension
echo ""
echo "🧩 Checking pgvector extension..."
PGVECTOR_CHECK=$(docker-compose exec -T postgres psql -U postgres -d lecture_summarizer_dev -t -c "SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector';")

if [ "$PGVECTOR_CHECK" -eq 1 ]; then
    echo "✅ pgvector extension is installed"
else
    echo "⚠️  pgvector extension not found, attempting to install..."
    docker-compose exec -T postgres psql -U postgres -d lecture_summarizer_dev -c "CREATE EXTENSION vector;"
    echo "✅ pgvector extension installed"
fi

# Test vector functionality
echo ""
echo "🧪 Testing vector functionality..."
docker-compose exec -T postgres psql -U postgres -d lecture_summarizer_dev << 'EOF' > /dev/null 2>&1
-- Create test table
DROP TABLE IF EXISTS _test_vectors;
CREATE TABLE _test_vectors (
    id SERIAL PRIMARY KEY,
    embedding vector(3)
);

-- Insert test data
INSERT INTO _test_vectors (embedding) VALUES ('[1,2,3]'::vector);

-- Test similarity search
SELECT embedding <-> '[1,2,3]'::vector AS distance FROM _test_vectors;

-- Clean up
DROP TABLE _test_vectors;
EOF

if [ $? -eq 0 ]; then
    echo "✅ Vector operations working correctly"
else
    echo "❌ Vector operations failed"
    exit 1
fi

# Check data persistence
echo ""
echo "💾 Checking data volume..."
VOLUME_EXISTS=$(docker volume ls | grep -c "lecture_summarizer_postgres_data" || true)
if [ "$VOLUME_EXISTS" -eq 1 ]; then
    echo "✅ Data volume exists (data will persist)"
else
    echo "⚠️  Data volume not found"
fi

# Display database info
echo ""
echo "📊 Database Information:"
echo "========================"
docker-compose exec -T postgres psql -U postgres -d lecture_summarizer_dev -c "
SELECT 
    version() AS postgresql_version;
"

echo ""
echo "📦 Installed Extensions:"
echo "========================"
docker-compose exec -T postgres psql -U postgres -d lecture_summarizer_dev -c "
SELECT 
    extname AS extension_name,
    extversion AS version
FROM pg_extension
WHERE extname != 'plpgsql'
ORDER BY extname;
"

echo ""
echo "✅ All verification checks passed!"
echo ""
echo "🎉 PostgreSQL with pgvector is ready to use!"
